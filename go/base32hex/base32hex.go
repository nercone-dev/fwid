// Package base32hex implements Base32 Hex (RFC 4648 section 7) with 'Z' as
// the padding character.
package base32hex

import (
	"errors"
	"fmt"
	"unicode/utf8"
)

const (
	// Alphabet is the Base32 Hex alphabet.
	Alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
	// Pad is the padding character.
	Pad = 'Z'
)

var (
	ErrLength          = errors.New("Base32Hex length must be a multiple of 8")
	ErrPaddingPosition = errors.New("Padding is only allowed in the last block")
	ErrPaddingLength   = errors.New("Invalid padding length")
	ErrTrailingBits    = errors.New("Non-zero trailing bits")
)

// CharacterError reports a character outside the alphabet.
type CharacterError struct{ Char rune }

func (e CharacterError) Error() string { return fmt.Sprintf("Invalid character: %q", e.Char) }

// bytesFromChars returns the bytes carried by a block with this many
// non-padding characters, or 0 if no block has that many.
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
	case c >= '0' && c <= '9':
		return uint64(c - '0'), true
	case c >= 'A' && c <= 'V':
		return uint64(c-'A') + 10, true
	}
	return 0, false
}

// Encode returns the padded Base32 Hex text of data.
func Encode(data []byte) string {
	out := make([]byte, 0, (len(data)+4)/5*8)
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
		for j := chars; j < 8; j++ {
			out = append(out, Pad)
		}
	}
	return string(out)
}

// Decode parses strictly padded Base32 Hex text.
func Decode(text string) ([]byte, error) {
	if len(text)%8 != 0 {
		return nil, ErrLength
	}
	blocks := len(text) / 8
	out := make([]byte, 0, blocks*5)
	for b := 0; b < blocks; b++ {
		block := text[b*8 : (b+1)*8]
		bodyLength := len(block)
		for bodyLength > 0 && block[bodyLength-1] == Pad {
			bodyLength--
		}
		if bodyLength != 8 && b != blocks-1 {
			return nil, ErrPaddingPosition
		}
		n := bytesFromChars(bodyLength)
		if n == 0 {
			return nil, ErrPaddingLength
		}
		var value uint64
		for i := 0; i < bodyLength; i++ {
			v, ok := index(block[i])
			if !ok {
				r, _ := utf8.DecodeRuneInString(block[i:])
				return nil, CharacterError{r}
			}
			value = value<<5 | v
		}
		extra := uint(bodyLength*5 - n*8)
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
