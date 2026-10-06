// bridge_server.go - Go 版游戏数据桥接服务器 (v1.26.0)
// 完全兼容 Python 版 bridge_server.py 接口:
//   GET /            -> 返回最新数据 json (浏览器扩展/插件轮询拉取)
//   POST /           -> 浏览器 hook 推数据 (浅合并 update + _recv_time)
// 性能: Go 并发 + 原生 JSON, 吞吐比 Python http.server 高一个量级
// 编译: go build bridge_server.go (Linux/Mac)
//        GOOS=windows GOARCH=amd64 go build -o bridge_server.exe bridge_server.go (Windows)
// 用法: bridge_server [--port 18899]
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"sync"
	"time"
)

var (
	mu     sync.RWMutex
	latest = map[string]any{}
)

func handleGet(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	// 锁内浅拷贝顶层map: 值引用共享(浏览器POST从不修改嵌套结构, 只替换顶层键),
	// 避免 Marshal 在锁外遍历时与 POST 并发写冲突
	mu.RLock()
	snap := make(map[string]any, len(latest))
	for k, v := range latest {
		snap[k] = v
	}
	mu.RUnlock()
	var b []byte
	if r.URL.Query().Get("pretty") == "1" {
		b, _ = json.MarshalIndent(snap, "", "  ")
	} else {
		b, _ = json.Marshal(snap)
	}
	w.Write(b)
}

func handlePost(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	body, _ := io.ReadAll(r.Body)
	var data map[string]any
	if json.Unmarshal(body, &data) == nil && data != nil {
		mu.Lock()
		for k, v := range data {
			latest[k] = v
		}
		// 与 Python time.time() 一致: float 秒
		latest["_recv_time"] = float64(time.Now().UnixNano()) / 1e9
		mu.Unlock()
	}
	w.Write([]byte("ok"))
}

func main() {
	port := flag.Int("port", 18899, "监听端口")
	flag.Parse()
	addr := fmt.Sprintf("127.0.0.1:%d", *port)

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			handleGet(w, r)
		} else {
			handlePost(w, r)
		}
	})

	fmt.Printf("[桥接] Go版服务器启动 http://%s\n", addr)

	// 状态打印协程 (模拟 Python 版控制台)
	go func() {
		for {
			time.Sleep(2 * time.Second)
			mu.RLock()
			rt, _ := latest["_recv_time"].(float64)
			mobs, _ := latest["mobs"].([]any)
			mobData, _ := latest["mobData"].(string)
			mu.RUnlock()
			if rt > 0 {
				age := float64(time.Now().UnixNano())/1e9 - rt
				fmt.Printf("[桥接] 最近数据 %.1fs前, mobs=%d, mobData长度=%d\n", age, len(mobs), len(mobData))
			} else {
				fmt.Println("[桥接] 等待中... (浏览器还没发数据)")
			}
		}
	}()

	if err := http.ListenAndServe(addr, nil); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
