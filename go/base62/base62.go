// Package base62 implements Base62 (0-9A-Za-z) over a big-endian
// arbitrary-precision integer, zero-padded to a length that depends only on
// the byte length.
package base62

import (
	"errors"
	"fmt"
	"unicode/utf8"
)

// Alphabet is the Base62 alphabet.
const Alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

var (
	ErrLength = errors.New("Invalid Base62 length")
	ErrRange  = errors.New("Value out of range")
)

// CharacterError reports a character outside the alphabet.
type CharacterError struct{ Char rune }

func (e CharacterError) Error() string { return fmt.Sprintf("Invalid character: %q", e.Char) }

func index(c byte) (uint32, bool) {
	switch {
	case c >= '0' && c <= '9':
		return uint32(c - '0'), true
	case c >= 'A' && c <= 'Z':
		return uint32(c-'A') + 10, true
	case c >= 'a' && c <= 'z':
		return uint32(c-'a') + 36, true
	}
	return 0, false
}

// divmod divides the big-endian number num in place and returns the remainder.
func divmod(num []byte, divisor uint32) uint32 {
	var rem uint32
	for i, b := range num {
		cur := rem<<8 | uint32(b)
		num[i] = byte(cur / divisor)
		rem = cur % divisor
	}
	return rem
}

func skipZeros(num []byte, start int) int {
	for start < len(num) && num[start] == 0 {
		start++
	}
	return start
}

// Length returns the smallest n such that 62^n >= 256^size, i.e. the number
// of base-62 digits of the largest size-byte value.
func Length(size int) int {
	num := make([]byte, size)
	for i := range num {
		num[i] = 0xFF
	}
	chars := 0
	for start := 0; start < len(num); start = skipZeros(num, start) {
		divmod(num[start:], 62)
		chars++
	}
	return chars
}

// Encode returns the fixed-length Base62 text of data.
func Encode(data []byte) string {
	width := Length(len(data))
	num := append([]byte(nil), data...)
	out := make([]byte, width)
	for i := range out {
		out[i] = Alphabet[0]
	}
	start := skipZeros(num, 0)
	for slot := width - 1; slot >= 0 && start < len(num); slot-- {
		out[slot] = Alphabet[divmod(num[start:], 62)]
		start = skipZeros(num, start)
	}
	return string(out)
}

// Decode parses fixed-length Base62 text.
func Decode(text string) ([]byte, error) {
	// log2(62) is irrational, so the estimate only seeds the search and the
	// exact length is always verified.
	estimate := int(float64(len(text)) * 5.954196310386876 / 8)
	size := -1
	for s := max(estimate-1, 0); s <= estimate+1; s++ {
		if Length(s) == len(text) {
			size = s
			break
		}
	}
	if size < 0 {
		return nil, ErrLength
	}
	out := make([]byte, size)
	for i := 0; i < len(text); i++ {
		carry, ok := index(text[i])
		if !ok {
			r, _ := utf8.DecodeRuneInString(text[i:])
			return nil, CharacterError{r}
		}
		for j := size - 1; j >= 0; j-- {
			cur := uint32(out[j])*62 + carry
			out[j] = byte(cur)
			carry = cur >> 8
		}
		if carry != 0 {
			return nil, ErrRange
		}
	}
	return out, nil
}
