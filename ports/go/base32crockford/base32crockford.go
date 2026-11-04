// Package base32crockford implements Crockford's Base32 without check symbols
// and without padding.
//
// Encoding emits uppercase symbols. Decoding is case-insensitive and maps the
// look-alike symbols I and L to 1 and O to 0, as Crockford specifies.
package base32crockford

import (
	"errors"
	"fmt"
	"unicode/utf8"
)

// Alphabet is the Crockford Base32 alphabet (no I, L, O, U).
const Alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

var (
	ErrLength       = errors.New("Invalid Base32Crockford length")
	ErrTrailingBits = errors.New("Non-zero trailing bits")
)

// CharacterError reports a character outside the alphabet.
type CharacterError struct{ Char rune }

func (e CharacterError) Error() string { return fmt.Sprintf("Invalid character: %q", e.Char) }

// bytesFromChars returns the bytes carried by a block with this many
// characters, or 0 if no block has that many.
func bytesFromChars(chars int) int {
	switch chars {
	case 8:
		return 5
	case 7:
		return 4
	case 5:
		return 3
	case 4:
		return 2
	case 2:
		return 1
	}
	return 0
}

func index(c byte) (uint64, bool) {
	switch {
	case c >= 'a' && c <= 'z':
		c -= 'a' - 'A'
	}
	switch c {
	case 'I', 'L':
		c = '1'
	case 'O':
		c = '0'
	}
	for i := 0; i < len(Alphabet); i++ {
		if Alphabet[i] == c {
			return uint64(i), true
		}
	}
	return 0, false
}

// Encode returns the unpadded uppercase Base32 text of data.
func Encode(data []byte) string {
	out := make([]byte, 0, (len(data)*8+4)/5)
	for i := 0; i < len(data); i += 5 {
		chunk := data[i:min(i+5, len(data))]
		n := len(chunk)
		var value uint64
		for _, b := range chunk {
			value = value<<8 | uint64(b)
		}
		value <<= 8 * uint(5-n)
		chars := (n*8 + 4) / 5
		for j := 0; j < chars; j++ {
			out = append(out, Alphabet[(value>>uint(35-5*j))&31])
		}
	}
	return string(out)
}

// Decode parses unpadded Base32 text.
func Decode(text string) ([]byte, error) {
	out := make([]byte, 0, len(text)/8*5+4)
	for start := 0; start < len(text); start += 8 {
		block := text[start:min(start+8, len(text))]
		n := bytesFromChars(len(block))
		if n == 0 {
			return nil, ErrLength
		}
		var value uint64
		for i := 0; i < len(block); i++ {
			v, ok := index(block[i])
			if !ok {
				r, _ := utf8.DecodeRuneInString(block[i:])
				return nil, CharacterError{r}
			}
			value = value<<5 | v
		}
		extra := uint(len(block)*5 - n*8)
		if value&(1<<extra-1) != 0 {
			return nil, ErrTrailingBits
		}
		value >>= extra
		for i := 0; i < n; i++ {
			out = append(out, byte(value>>uint(8*(n-1-i))))
		}
	}
	return out, nil
}
