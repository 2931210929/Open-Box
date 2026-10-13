// Local, deterministic HTTP/DNS fixtures for release performance checks.
// No external traffic or subscriptions are used. Build with CGO_ENABLED=0.
package main

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"flag"
	"io"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

func answer(q []byte) []byte {
	if len(q) < 13 {
		return nil
	}
	at := 12
	var labels []string
	for at < len(q) && q[at] != 0 {
		n := int(q[at])
		at++
		if n > 63 || at+n >= len(q) {
			return nil
		}
		labels = append(labels, string(q[at:at+n]))
		at += n
	}
	at++
	if at+4 > len(q) {
		return nil
	}
	h := append([]byte(nil), q[:at+4]...)
	binary.BigEndian.PutUint16(h[2:4], 0x8180)
	binary.BigEndian.PutUint16(h[6:8], 0)
	binary.BigEndian.PutUint16(h[8:10], 0)
	binary.BigEndian.PutUint16(h[10:12], 0)
	if binary.BigEndian.Uint16(q[at:at+2]) == 1 {
		ip := byte(8)
		if strings.HasPrefix(strings.Join(labels, "."), "direct.") {
			ip = 7
		}
		binary.BigEndian.PutUint16(h[6:8], 1)
		h = append(h, 0xc0, 0x0c, 0, 1, 0, 1, 0, 0, 0, 60, 0, 4, 198, 51, 100, ip)
	}
	return h
}

func server() {
	udp, err := net.ListenPacket("udp4", ":53")
	if err != nil {
		panic(err)
	}
	go func() {
		b := make([]byte, 4096)
		for {
			n, peer, err := udp.ReadFrom(b)
			if err != nil {
				return
			}
			if r := answer(b[:n]); r != nil {
				_, _ = udp.WriteTo(r, peer)
			}
		}
	}()
	tcp, err := net.Listen("tcp4", ":53")
	if err != nil {
		panic(err)
	}
	go func() {
		for {
			c, err := tcp.Accept()
			if err != nil {
				return
			}
			go func() {
				defer c.Close()
				_ = c.SetDeadline(time.Now().Add(30 * time.Second))
				var length [2]byte
				for {
					if _, err := io.ReadFull(c, length[:]); err != nil {
						return
					}
					n := int(binary.BigEndian.Uint16(length[:]))
					if n > 4096 {
						return
					}
					b := make([]byte, n)
					if _, err := io.ReadFull(c, b); err != nil {
						return
					}
					r := answer(b)
					if r == nil {
						return
					}
					binary.BigEndian.PutUint16(length[:], uint16(len(r)))
					if _, err := c.Write(append(length[:], r...)); err != nil {
						return
					}
				}
			}()
		}
	}()
	block := make([]byte, 256*1024)
	for i := range block {
		block[i] = byte(i)
	}
	http.HandleFunc("/fixture", func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"source": strings.Split(r.RemoteAddr, ":")[0], "fixture": true})
	})
	http.HandleFunc("/bulk", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/octet-stream")
		for {
			if _, err := w.Write(block); err != nil {
				return
			}
			select {
			case <-r.Context().Done():
				return
			default:
			}
		}
	})
	if err := http.ListenAndServe(":8080", nil); err != nil {
		panic(err)
	}
}

func load() {
	f := flag.NewFlagSet("load", flag.ExitOnError)
	seconds := f.Int("seconds", 15, "measurement duration")
	parallel := f.Int("parallel", 4, "HTTP streams")
	rate := f.Float64("mbps", 0, "aggregate rate limit; zero is unlimited")
	_ = f.Parse(os.Args[2:])
	if f.NArg() != 1 || *seconds < 1 || *seconds > 300 || *parallel < 1 || *parallel > 32 || *rate < 0 {
		panic("invalid load arguments")
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(*seconds)*time.Second)
	defer cancel()
	transport := &http.Transport{Proxy: nil, MaxIdleConnsPerHost: *parallel, DisableCompression: true}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport}
	var bytes, failures atomic.Int64
	var wg sync.WaitGroup
	start := time.Now()
	for i := 0; i < *parallel; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			req, err := http.NewRequestWithContext(ctx, "GET", f.Arg(0), nil)
			if err != nil {
				panic(err)
			}
			res, err := client.Do(req)
			if err != nil {
				failures.Add(1)
				return
			}
			defer res.Body.Close()
			if res.StatusCode != 200 {
				failures.Add(1)
				return
			}
			b := make([]byte, 64*1024)
			var received int64
			for {
				n, err := res.Body.Read(b)
				bytes.Add(int64(n))
				received += int64(n)
				if err != nil {
					if ctx.Err() == nil {
						failures.Add(1)
					}
					return
				}
				if *rate > 0 {
					target := time.Duration(float64(received) * 8 * float64(*parallel) / (*rate * 1e6) * float64(time.Second))
					delay := target - time.Since(start)
					if delay > 0 {
						timer := time.NewTimer(delay)
						select {
						case <-ctx.Done():
							timer.Stop()
							return
						case <-timer.C:
						}
					}
				}
			}
		}()
	}
	wg.Wait()
	elapsed := time.Since(start).Seconds()
	_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"seconds": elapsed, "parallel": *parallel, "bytes": bytes.Load(), "mbps": float64(bytes.Load()) * 8 / elapsed / 1e6, "rateLimitMbps": *rate, "errors": failures.Load()})
	if failures.Load() > 0 || bytes.Load() == 0 {
		os.Exit(1)
	}
}

func main() {
	if len(os.Args) < 2 {
		panic("server or load required")
	}
	switch os.Args[1] {
	case "server":
		server()
	case "load":
		load()
	default:
		panic("unknown command")
	}
}
