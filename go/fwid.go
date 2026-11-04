// Package fwid implements FWID (FourWord Identifier): random identifiers with
// a time-sortable prefix. An FWID is a quarter timestamp (milliseconds since
// 2001-01-01 00:00:00 UTC) followed by three quarters of CSPRNG output.
package fwid

import (
	"crypto/rand"
	"math"
	"math/bits"
	"strings"
	"time"

	"github.com/nercone-dev/fwid/go/base32hex"
	"github.com/nercone-dev/fwid/go/base62"
)

// Format is a representation of an FWID.
type Format int

const (
	Unformatted Format = iota
	StandardText
	ReadableText
	CompactText
)

// Name returns the human-readable name of the format.
func (f Format) Name() string {
	switch f {
	case Unformatted:
		return "Unformatted"
	case StandardText:
		return "Standard Text"
	case ReadableText:
		return "Readable Text"
	case CompactText:
		return "Compact Text"
	}
	return "Unknown"
}

func (f Format) String() string { return f.Name() }

// Detect returns the text format of text; the first format that parses wins,
// in the order Standard, Readable, Compact.
func Detect(text string) (Format, error) {
	format, _, err := Parse(text)
	return format, err
}

const (
	// EpochUnixMS is the FWID epoch, 2001-01-01 00:00:00 UTC, in Unix milliseconds.
	EpochUnixMS = 978307200000
	// BitsAlign is the granularity of the total bit length.
	BitsAlign = 32
)

// FWID is an immutable identifier. It is comparable and usable as a map key.
type FWID struct{ raw string }

// New generates an FWID of the smallest size that fits the current time.
func New() (FWID, error) { return Generate(0, time.Time{}) }

// FromBytes wraps a copy of raw, whose length must be a positive multiple of 4.
func FromBytes(raw []byte) (FWID, error) {
	if len(raw) == 0 || len(raw)%(BitsAlign/8) != 0 {
		return FWID{}, ErrBits
	}
	return FWID{string(raw)}, nil
}

func FromStandardText(text string) (FWID, error) {
	raw, err := base32hex.Decode(text)
	if err != nil {
		return FWID{}, err
	}
	return FromBytes(raw)
}

func FromReadableText(text string) (FWID, error) {
	if strings.ToLower(text) != text {
		return FWID{}, ErrReadableCase
	}
	groups := strings.Split(text, "-")
	for _, group := range groups {
		if len(group) != 8 {
			return FWID{}, ErrReadableGroups
		}
	}
	return FromStandardText(strings.ToUpper(strings.Join(groups, "")))
}

func FromCompactText(text string) (FWID, error) {
	raw, err := base62.Decode(text)
	if err != nil {
		return FWID{}, err
	}
	return FromBytes(raw)
}

// Parse parses text in any text format and reports which one matched.
func Parse(text string) (Format, FWID, error) {
	if id, err := FromStandardText(text); err == nil {
		return StandardText, id, nil
	}
	if id, err := FromReadableText(text); err == nil {
		return ReadableText, id, nil
	}
	if id, err := FromCompactText(text); err == nil {
		return CompactText, id, nil
	}
	return Unformatted, FWID{}, ErrUnknownFormat
}

// FromText parses text in any text format.
func FromText(text string) (FWID, error) {
	_, id, err := Parse(text)
	return id, err
}

// CheckBits reports whether n is a positive multiple of BitsAlign.
func CheckBits(n int) error {
	if n < BitsAlign || n%BitsAlign != 0 {
		return ErrBits
	}
	return nil
}

// EpochMS returns the milliseconds from the FWID epoch to t. The zero Time means now.
func EpochMS(t time.Time) (uint64, error) {
	if t.IsZero() {
		t = time.Now()
	}
	ms := t.UnixMilli() - EpochUnixMS
	if ms < 0 {
		return 0, ErrBeforeEpoch
	}
	return uint64(ms), nil
}

func bytesFor(ms uint64) int {
	return max(1, (bits.Len64(ms)+7)/8)
}

// MinBits returns the smallest bit length that fits the timestamp of t. The zero Time means now.
func MinBits(t time.Time) (int, error) {
	ms, err := EpochMS(t)
	if err != nil {
		return 0, err
	}
	return bytesFor(ms) * BitsAlign, nil
}

// Generate returns an FWID of n bits embedding t. Zero n means the smallest
// size that fits the timestamp; the zero Time means now.
func Generate(n int, t time.Time) (FWID, error) {
	ms, err := EpochMS(t)
	if err != nil {
		return FWID{}, err
	}
	required := bytesFor(ms) * BitsAlign
	if n == 0 {
		n = required
	}
	if err := CheckBits(n); err != nil {
		return FWID{}, err
	}
	if n < required {
		return FWID{}, TimestampTooLargeError{Bits: n, Required: required}
	}
	raw := make([]byte, n/8)
	timestampLength := len(raw) / 4
	for i, v := timestampLength-1, ms; i >= 0 && v > 0; i, v = i-1, v>>8 {
		raw[i] = byte(v)
	}
	if _, err := rand.Read(raw[timestampLength:]); err != nil {
		return FWID{}, err
	}
	return FWID{string(raw)}, nil
}

// Bytes returns a copy of the raw bytes.
func (f FWID) Bytes() []byte { return []byte(f.raw) }

func (f FWID) Bits() int          { return len(f.raw) * 8 }
func (f FWID) BitsTimestamp() int { return len(f.raw) * 2 }
func (f FWID) BitsRandom() int    { return len(f.raw) * 6 }

// TimestampMS returns the milliseconds from the FWID epoch stored in the timestamp field.
func (f FWID) TimestampMS() (uint64, error) {
	field := f.raw[:len(f.raw)/4]
	split := max(len(field)-8, 0)
	for i := 0; i < split; i++ {
		if field[i] != 0 {
			return 0, ErrTimestampOverflow
		}
	}
	var ms uint64
	for i := split; i < len(field); i++ {
		ms = ms<<8 | uint64(field[i])
	}
	return ms, nil
}

// Timestamp returns the embedded time in UTC.
func (f FWID) Timestamp() (time.Time, error) {
	ms, err := f.TimestampMS()
	if err != nil {
		return time.Time{}, err
	}
	if ms > math.MaxInt64-EpochUnixMS {
		return time.Time{}, ErrTimeOutOfRange
	}
	return time.UnixMilli(int64(ms) + EpochUnixMS).UTC(), nil
}

// Text returns the text of the given text format.
func (f FWID) Text(format Format) (string, error) {
	switch format {
	case StandardText:
		return f.StandardText(), nil
	case ReadableText:
		return f.ReadableText(), nil
	case CompactText:
		return f.CompactText(), nil
	}
	return "", ErrNotTextFormat
}

func (f FWID) StandardText() string { return base32hex.Encode([]byte(f.raw)) }

func (f FWID) ReadableText() string {
	standard := strings.ToLower(f.StandardText())
	var out strings.Builder
	out.Grow(len(standard) + len(standard)/8)
	for i := 0; i < len(standard); i += 8 {
		if i > 0 {
			out.WriteByte('-')
		}
		out.WriteString(standard[i : i+8])
	}
	return out.String()
}

func (f FWID) CompactText() string { return base62.Encode([]byte(f.raw)) }

func (f FWID) String() string { return f.StandardText() }

// Compare orders by the raw bytes, which is time order for equal bit lengths.
func (f FWID) Compare(other FWID) int { return strings.Compare(f.raw, other.raw) }
