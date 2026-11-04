// Extract method-specific, import-free Go examples using Go's parser.
// Input is a JSON object mapping method identifiers to sample requests.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type declaration struct {
	node  ast.Decl
	names []string
}

func receiverName(expr ast.Expr) string {
	if pointer, ok := expr.(*ast.StarExpr); ok {
		expr = pointer.X
	}
	if identifier, ok := expr.(*ast.Ident); ok {
		return identifier.Name
	}
	return ""
}

func main() {
	folder := flag.String("package", "single", "engine package directory")
	flag.Parse()
	if err := generate(*folder); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func generate(folder string) error {
	fileset := token.NewFileSet()
	paths, err := filepath.Glob(filepath.Join(folder, "*.go"))
	if err != nil {
		return err
	}
	var declarations []declaration
	byName := map[string]int{}
	methods := map[string][]int{}
	imports := map[string]string{}
	for _, path := range paths {
		if strings.HasSuffix(path, "_test.go") {
			continue
		}
		file, err := parser.ParseFile(fileset, path, nil, 0)
		if err != nil {
			return err
		}
		for _, node := range file.Decls {
			entry := declaration{node: node}
			switch node := node.(type) {
			case *ast.FuncDecl:
				if node.Recv != nil {
					name := receiverName(node.Recv.List[0].Type)
					methods[name] = append(methods[name], len(declarations))
				} else {
					entry.names = []string{node.Name.Name}
				}
			case *ast.GenDecl:
				if node.Tok == token.IMPORT {
					for _, spec := range node.Specs {
						spec := spec.(*ast.ImportSpec)
						path, err := strconv.Unquote(spec.Path.Value)
						if err != nil {
							return err
						}
						name := filepath.Base(path)
						if spec.Name != nil {
							name = spec.Name.Name
						}
						if name == "_" || name == "." {
							return fmt.Errorf("unsupported import alias %q", name)
						}
						imports[name] = path
					}
					continue
				}
				for _, spec := range node.Specs {
					switch spec := spec.(type) {
					case *ast.TypeSpec:
						entry.names = append(entry.names, spec.Name.Name)
					case *ast.ValueSpec:
						for _, name := range spec.Names {
							entry.names = append(entry.names, name.Name)
						}
					}
				}
			}
			for _, name := range entry.names {
				byName[name] = len(declarations)
			}
			declarations = append(declarations, entry)
		}
	}
	var requests map[string]json.RawMessage
	if err := json.NewDecoder(os.Stdin).Decode(&requests); err != nil {
		return err
	}
	output := map[string]string{}
	for method, request := range requests {
		var entry strings.Builder
		entry.WriteString("Count")
		for _, part := range strings.Split(method, "-") {
			entry.WriteString(strings.ToUpper(part[:1]) + part[1:])
		}
		function := entry.String()
		index, exists := byName[function]
		if !exists {
			return fmt.Errorf("missing entry point %s", function)
		}
		selected := map[int]bool{}
		neededImports := map[string]string{"json": "encoding/json", "os": "os"}
		pending := []int{index}
		for len(pending) > 0 {
			index := pending[len(pending)-1]
			pending = pending[:len(pending)-1]
			if selected[index] {
				continue
			}
			selected[index] = true
			ast.Inspect(declarations[index].node, func(node ast.Node) bool {
				if identifier, ok := node.(*ast.Ident); ok {
					if dependency, exists := byName[identifier.Name]; exists {
						pending = append(pending, dependency)
					}
					pending = append(pending, methods[identifier.Name]...)
				}
				if selector, ok := node.(*ast.SelectorExpr); ok {
					if identifier, ok := selector.X.(*ast.Ident); ok {
						if path, exists := imports[identifier.Name]; exists {
							neededImports[identifier.Name] = path
						}
					}
				}
				return true
			})
		}
		var source bytes.Buffer
		source.WriteString("// Go 1.23+. Save as example.go and run: go run example.go\n// Self-contained count, extracted from the validated Go engine.\npackage main\n\nimport (\n")
		names := make([]string, 0, len(neededImports))
		for name := range neededImports {
			names = append(names, name)
		}
		sort.Strings(names)
		for _, name := range names {
			fmt.Fprintf(&source, "%s %q\n", name, neededImports[name])
		}
		source.WriteString(")\n\n")
		for index, declaration := range declarations {
			if selected[index] {
				if err := format.Node(&source, fileset, declaration.node); err != nil {
					return err
				}
				source.WriteString("\n\n")
			}
		}
		fmt.Fprintf(&source, `func main() {
    var request any
    if err := json.Unmarshal([]byte(%s), &request); err != nil { panic(err) }
    answer, err := %s(request)
    if err != nil { panic(err) }
    encoder := json.NewEncoder(os.Stdout)
    encoder.SetIndent("", "  ")
    if err := encoder.Encode(answer); err != nil { panic(err) }
}
`, strconv.Quote(string(request)), function)
		formatted, err := format.Source(source.Bytes())
		if err != nil {
			return fmt.Errorf("%s: %w", method, err)
		}
		output[method] = string(formatted)
	}
	return json.NewEncoder(os.Stdout).Encode(output)
}
