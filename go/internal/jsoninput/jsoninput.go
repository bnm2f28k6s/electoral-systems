// Package jsoninput rejects lossy Unicode decoding at the Go CLI boundary.
package jsoninput

import (
	"encoding/json"
	"errors"
	"io"
	"strconv"
	"unicode/utf8"
)

// Decode reads one JSON value without replacing invalid UTF-8 or lone UTF-16
// surrogates with U+FFFD, which could silently change candidate identifiers.
func Decode(input io.Reader) (any, error) {
	data, err := io.ReadAll(input)
	if err != nil {
		return nil, err
	}
	if !utf8.Valid(data) {
		return nil, errors.New("JSON must contain valid UTF-8")
	}
	for index := 0; index < len(data); index++ {
		if data[index] != '\\' {
			continue
		}
		index++
		if index >= len(data) || data[index] != 'u' || index+4 >= len(data) {
			continue
		}
		value, err := strconv.ParseUint(string(data[index+1:index+5]), 16, 16)
		if err != nil {
			continue
		} // encoding/json reports malformed escapes.
		index += 4
		if value >= 0xdc00 && value <= 0xdfff {
			return nil, errors.New("JSON contains an unpaired UTF-16 surrogate")
		}
		if value < 0xd800 || value > 0xdbff {
			continue
		}
		if index+6 >= len(data) || data[index+1] != '\\' || data[index+2] != 'u' {
			return nil, errors.New("JSON contains an unpaired UTF-16 surrogate")
		}
		low, err := strconv.ParseUint(string(data[index+3:index+7]), 16, 16)
		if err != nil || low < 0xdc00 || low > 0xdfff {
			return nil, errors.New("JSON contains an unpaired UTF-16 surrogate")
		}
		index += 6
	}
	var request any
	if err := json.Unmarshal(data, &request); err != nil {
		return nil, err
	}
	return request, nil
}
