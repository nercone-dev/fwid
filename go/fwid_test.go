package fwid_test

import (
	"bytes"
	"encoding/hex"
	"errors"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"

	fwid "github.com/nercone-dev/fwid/go"
	"github.com/nercone-dev/fwid/go/base32hex"
	"github.com/nercone-dev/fwid/go/base62"
	"github.com/nercone-dev/fwid/go/iso8601"
)

func rows(t *testing.T, name string) [][]string {
	t.Helper()
	data, err := os.ReadFile("../testdata/" + name)
	if err != nil {
		t.Fatal(err)
	}
	var out [][]string
	for _, line := range strings.Split(string(data), "\n") {
		if line != "" && !strings.HasPrefix(line, "#") {
			out = append(out, strings.Split(line, "\t"))
		}
	}
	return out
}

func at(unixMS int64) time.Time { return time.UnixMilli(unixMS) }

func TestSharedVectors(t *testing.T) {
	vectors := rows(t, "vectors.tsv")
	if len(vectors) == 0 {
		t.Fatal("no vectors")
	}
	for _, f := range vectors {
		raw, err := hex.DecodeString(f[0])
		if err != nil {
			t.Fatal(err)
		}
		id, err := fwid.FromBytes(raw)
		if err != nil {
			t.Fatal(err)
		}
		if id.StandardText() != f[1] || id.ReadableText() != f[2] || id.CompactText() != f[3] {
			t.Errorf("%s: texts differ: %s %s %s", f[0], id.StandardText(), id.ReadableText(), id.CompactText())
		}
		if f[4] != "-" {
			if ms, err := id.TimestampMS(); err != nil || strconv.FormatUint(ms, 10) != f[4] {
				t.Errorf("%s: timestamp %d %v, want %s", f[0], ms, err, f[4])
			}
		}
		for i, format := range []fwid.Format{fwid.StandardText, fwid.ReadableText, fwid.CompactText} {
			text := f[1+i]
			detected, parsed, err := fwid.Parse(text)
			if err != nil || detected != format || !bytes.Equal(parsed.Bytes(), raw) {
				t.Errorf("%s: parse = %v %v %v, want %v", text, detected, parsed, err, format)
			}
		}
	}
}

func TestInvalidTextsAreRejected(t *testing.T) {
	texts := []string{""}
	for _, f := range rows(t, "invalid.tsv") {
		texts = append(texts, f[0])
	}
	for _, text := range texts {
		if _, err := fwid.FromText(text); err == nil {
			t.Errorf("%q accepted", text)
		}
		if _, err := fwid.Detect(text); !errors.Is(err, fwid.ErrUnknownFormat) {
			t.Errorf("%q: Detect error = %v", text, err)
		}
	}
}

// RFC 4648 section 10, with '=' replaced by 'Z'.
func TestBase32HexRFC4648Vectors(t *testing.T) {
	for _, c := range [][2]string{
		{"", ""}, {"f", "COZZZZZZ"}, {"fo", "CPNGZZZZ"}, {"foo", "CPNMUZZZ"},
		{"foob", "CPNMUOGZ"}, {"fooba", "CPNMUOJ1"}, {"foobar", "CPNMUOJ1E8ZZZZZZ"},
	} {
		if got := base32hex.Encode([]byte(c[0])); got != c[1] {
			t.Errorf("Encode(%q) = %q, want %q", c[0], got, c[1])
		}
		if got, err := base32hex.Decode(c[1]); err != nil || string(got) != c[0] {
			t.Errorf("Decode(%q) = %q, %v", c[1], got, err)
		}
	}
}

func TestBase32HexRejectsMalformedInput(t *testing.T) {
	for _, text := range []string{"C", "COZZZZZ", "CZZZZZZZ", "COZZZZZZCOZZZZZZ", "COzzzzzz", "C1ZZZZZZ", "CPNMUOJé"} {
		if _, err := base32hex.Decode(text); err == nil {
			t.Errorf("%q accepted", text)
		}
	}
}

func TestBase62LengthsAndRoundTrip(t *testing.T) {
	for size, want := range map[int]int{0: 0, 1: 2, 4: 6, 16: 22, 32: 43} {
		if got := base62.Length(size); got != want {
			t.Errorf("Length(%d) = %d, want %d", size, got, want)
		}
	}
	for size := 0; size < 40; size++ {
		data := make([]byte, size)
		for i := range data {
			data[i] = byte(i*37 + 11)
		}
		text := base62.Encode(data)
		if len(text) != base62.Length(size) {
			t.Errorf("size %d: len = %d", size, len(text))
		}
		if got, err := base62.Decode(text); err != nil || !bytes.Equal(got, data) {
			t.Errorf("size %d: round trip = %x, %v", size, got, err)
		}
	}
}

func TestBase62RejectsMalformedInput(t *testing.T) {
	for _, text := range []string{"0", "zzzzzz", "00000-", "00000é"} {
		if _, err := base62.Decode(text); err == nil {
			t.Errorf("%q accepted", text)
		}
	}
}

func TestGenerateLayout(t *testing.T) {
	when := at(1_704_067_200_000)
	const ms = 725_760_000_000
	if got, err := fwid.EpochMS(when); err != nil || got != ms {
		t.Fatalf("EpochMS = %d, %v", got, err)
	}
	if got, err := fwid.MinBits(when); err != nil || got != 160 {
		t.Fatalf("MinBits = %d, %v", got, err)
	}
	for n := 160; n <= 512; n += 32 {
		id, err := fwid.Generate(n, when)
		if err != nil {
			t.Fatal(err)
		}
		if id.Bits() != n || id.BitsTimestamp() != n/4 || id.BitsRandom() != n/4*3 {
			t.Errorf("%d: bits %d/%d/%d", n, id.Bits(), id.BitsTimestamp(), id.BitsRandom())
		}
		if got, err := id.TimestampMS(); err != nil || got != ms {
			t.Errorf("%d: TimestampMS = %d, %v", n, got, err)
		}
		if got, err := id.Timestamp(); err != nil || !got.Equal(when) {
			t.Errorf("%d: Timestamp = %v, %v", n, got, err)
		}
		field := id.Bytes()[:n/32]
		if !bytes.HasSuffix(field, []byte{0xA8, 0xFA, 0xAA, 0xC0, 0x00}) || len(bytes.TrimLeft(field[:len(field)-5], "\x00")) != 0 {
			t.Errorf("%d: timestamp field %x", n, field)
		}
	}
}

func TestGenerateRejectsBadSizes(t *testing.T) {
	when := at(1_704_067_200_000)
	for _, n := range []int{-32, 31, 33, 161} {
		if _, err := fwid.Generate(n, when); !errors.Is(err, fwid.ErrBits) {
			t.Errorf("%d: err = %v", n, err)
		}
	}
	var tooLarge fwid.TimestampTooLargeError
	if _, err := fwid.Generate(128, when); !errors.As(err, &tooLarge) || tooLarge.Required != 160 {
		t.Errorf("128: err = %v", err)
	}
	if _, err := fwid.Generate(0, at(978_307_199_999)); !errors.Is(err, fwid.ErrBeforeEpoch) {
		t.Errorf("before epoch: err = %v", err)
	}
	if _, err := fwid.Generate(0, at(978_307_200_000)); err != nil {
		t.Errorf("at epoch: err = %v", err)
	}
	for _, raw := range [][]byte{{0, 0, 0}, {}} {
		if _, err := fwid.FromBytes(raw); !errors.Is(err, fwid.ErrBits) {
			t.Errorf("%x: err = %v", raw, err)
		}
	}
}

func TestIDsSortByTime(t *testing.T) {
	a, _ := fwid.Generate(256, at(1_000_000_000_000))
	b, _ := fwid.Generate(256, at(1_000_000_000_001))
	if a.Compare(b) >= 0 || a.StandardText() >= b.StandardText() {
		t.Error("ids do not sort by time")
	}
	x, _ := fwid.New()
	y, _ := fwid.New()
	if x == y {
		t.Error("two new ids are equal")
	}
}

func TestISO8601ParseAndFormat(t *testing.T) {
	for text, unixMS := range map[string]int64{
		"2024-01-01T00:00:00Z":        1_704_067_200_000,
		"2024-01-01":                  1_704_067_200_000,
		"2024-01-01 00:00":            1_704_067_200_000,
		"2024-01-01T09:00:00+09:00":   1_704_067_200_000,
		"2024-01-01T09:00:00+0900":    1_704_067_200_000,
		"2023-12-31T19:00:00-05":      1_704_067_200_000,
		"2024-02-29T12:34:56.789123Z": 1_709_210_096_789,
		"2024-02-29T12:34:56.5":       1_709_210_096_500,
		"1970-01-01T00:00:00Z":        0,
	} {
		if got, err := iso8601.Parse(text); err != nil || got.UnixMilli() != unixMS {
			t.Errorf("Parse(%q) = %v, %v; want %d", text, got, err, unixMS)
		}
	}
	if got := iso8601.Format(at(1_709_210_096_789)); got != "2024-02-29T12:34:56.789+00:00" {
		t.Errorf("Format = %q", got)
	}
	for _, text := range []string{
		"", "2024", "2024-13-01", "2023-02-29", "2024-04-31", "2024-01-01T24:00", "2024-01-01T00:60",
		"2024-01-01T00:00:60", "2024-01-01T00", "2024-01-01T00:00:00.", "2024-01-01T00:00:00+24:00",
		"2024-01-01T00:00:00Zx", "2024-01-01Z", "24-01-01", "2024-01-01T00:00:00 +09:00",
	} {
		if _, err := iso8601.Parse(text); !errors.Is(err, iso8601.ErrInvalid) {
			t.Errorf("Parse(%q) err = %v", text, err)
		}
	}
}

func TestTextRejectsUnformatted(t *testing.T) {
	id, _ := fwid.New()
	if _, err := id.Text(fwid.Unformatted); !errors.Is(err, fwid.ErrNotTextFormat) {
		t.Errorf("err = %v", err)
	}
	if got, _ := id.Text(fwid.StandardText); got != id.String() {
		t.Errorf("Text = %q, String = %q", got, id.String())
	}
}
