package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestExtractsDependencyClosureAndReceiverMethods(t *testing.T) {
	directory := t.TempDir()
	source := `package engine
import ("math"; "sort")
type problem struct{}
func (*problem) Error() string { return "bad request" }
const scale = 3
func helper() float64 { return math.Max(scale, 2) }
func CountDemo(request any) (map[string]any, error) {
    if request == nil { return nil, &problem{} }
    return map[string]any{"value": helper()}, nil
}
func unrelated() { sort.Ints([]int{2, 1}) }
`
	if err := os.WriteFile(filepath.Join(directory, "engine.go"), []byte(source), 0600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("go", "run", ".", "-package", directory)
	command.Stdin = strings.NewReader(`{"demo": {"method":"demo"}}`)
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("extract: %v\n%s", err, output)
	}
	var examples map[string]string
	if err := json.Unmarshal(output, &examples); err != nil {
		t.Fatal(err)
	}
	example := examples["demo"]
	if strings.Contains(example, "unrelated") || strings.Contains(example, `"sort"`) {
		t.Fatal("unrelated declarations or imports were retained")
	}
	if !strings.Contains(example, "Error() string") {
		t.Fatal("receiver method was lost")
	}
	path := filepath.Join(directory, "example.go")
	if err := os.WriteFile(path, []byte(example), 0600); err != nil {
		t.Fatal(err)
	}
	output, err = exec.Command("go", "run", path).CombinedOutput()
	if err != nil {
		t.Fatalf("run extracted example: %v\n%s", err, output)
	}
	var result map[string]any
	if err := json.Unmarshal(output, &result); err != nil {
		t.Fatal(err)
	}
	if result["value"] != float64(3) {
		t.Fatalf("unexpected example result: %s", output)
	}
}

func TestMissingEntryPointFails(t *testing.T) {
	directory := t.TempDir()
	if err := os.WriteFile(filepath.Join(directory, "engine.go"), []byte("package engine\n"), 0600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("go", "run", ".", "-package", directory)
	command.Stdin = strings.NewReader(`{"unknown": {}}`)
	output, err := command.CombinedOutput()
	if err == nil || !strings.Contains(string(output), "missing entry point CountUnknown") {
		t.Fatalf("expected explicit error, got %v: %s", err, output)
	}
}
