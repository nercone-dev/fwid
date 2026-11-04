package fwid

import (
	"errors"
	"fmt"
)

var (
	// ErrBits reports a bit length that is not a positive multiple of 32.
	ErrBits = errors.New("Bits must be a positive multiple of 32")
	// ErrBeforeEpoch reports a time before 2001-01-01 00:00:00 UTC.
	ErrBeforeEpoch = errors.New("datetime must not be before the FWID epoch (2001-01-01 00:00:00 UTC)")
	// ErrTimestampOverflow reports a timestamp field that does not fit in 64 bits.
	ErrTimestampOverflow = errors.New("timestamp does not fit in 64 bits")
	// ErrTimeOutOfRange reports a point in time that cannot be represented.
	ErrTimeOutOfRange = errors.New("datetime is out of range")
	// ErrUnknownFormat reports text that is in no known FWID text format.
	ErrUnknownFormat = errors.New("Unknown Format")
	// ErrNotTextFormat reports a format that is not a text format.
	ErrNotTextFormat = errors.New("Format is not Text-based Format")
	// ErrReadableCase reports uppercase characters in Readable Text.
	ErrReadableCase = errors.New("Readable Text must be lowercase")
	// ErrReadableGroups reports Readable Text groups that are not 8 characters long.
	ErrReadableGroups = errors.New("Readable Text must be split into groups of 8 characters")
)

// TimestampTooLargeError reports a timestamp that does not fit in the requested size.
type TimestampTooLargeError struct{ Bits, Required int }

func (e TimestampTooLargeError) Error() string {
	return fmt.Sprintf("%d bits is too small for this timestamp (need at least %d)", e.Bits, e.Required)
}
