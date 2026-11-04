// Package iso8601 parses and formats extended-format ISO 8601 datetimes with
// millisecond precision.
//
// Accepted input: YYYY-MM-DD optionally followed by 'T', 't' or a space and
// hh:mm[:ss[.fraction]], then optionally 'Z' or an offset +hh[:mm] / +hhmm.
// Values without an offset are UTC. Digits beyond milliseconds are truncated.
package iso8601

import (
	"errors"
	"time"
)

// ErrInvalid is returned for text that is not an accepted datetime.
var ErrInvalid = errors.New("invalid ISO 8601 datetime")

type scanner struct {
	text string
	pos  int
}

// digits consumes exactly count ASCII digits.
func (s *scanner) digits(count int) (int, bool) {
	if s.pos+count > len(s.text) {
		return 0, false
	}
	value := 0
	for _, c := range []byte(s.text[s.pos : s.pos+count]) {
		if c < '0' || c > '9' {
			return 0, false
		}
		value = value*10 + int(c-'0')
	}
	s.pos += count
	return value, true
}

func (s *scanner) accept(c byte) bool {
	if s.pos < len(s.text) && s.text[s.pos] == c {
		s.pos++
		return true
	}
	return false
}

func (s *scanner) done() bool { return s.pos == len(s.text) }

func daysInMonth(year, month int) int {
	return time.Date(year, time.Month(month)+1, 0, 0, 0, 0, 0, time.UTC).Day()
}

// Parse parses text into a UTC time.
func Parse(text string) (time.Time, error) {
	s := &scanner{text: text}
	year, ok1 := s.digits(4)
	dash1 := s.accept('-')
	month, ok2 := s.digits(2)
	dash2 := s.accept('-')
	day, ok3 := s.digits(2)
	if !(ok1 && dash1 && ok2 && dash2 && ok3) || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month) {
		return time.Time{}, ErrInvalid
	}
	var hour, minute, second, millis, offset int
	if !s.done() {
		if !(s.accept('T') || s.accept('t') || s.accept(' ')) {
			return time.Time{}, ErrInvalid
		}
		var okh, okm bool
		hour, okh = s.digits(2)
		colon := s.accept(':')
		minute, okm = s.digits(2)
		if !(okh && colon && okm) {
			return time.Time{}, ErrInvalid
		}
		if s.accept(':') {
			var ok bool
			if second, ok = s.digits(2); !ok {
				return time.Time{}, ErrInvalid
			}
			if s.accept('.') || s.accept(',') {
				start := s.pos
				for s.pos < len(text) && text[s.pos] >= '0' && text[s.pos] <= '9' {
					s.pos++
				}
				if s.pos == start {
					return time.Time{}, ErrInvalid
				}
				for i := 0; i < 3; i++ {
					d := 0
					if start+i < s.pos {
						d = int(text[start+i] - '0')
					}
					millis = millis*10 + d
				}
			}
		}
		if hour > 23 || minute > 59 || second > 59 {
			return time.Time{}, ErrInvalid
		}
		switch {
		case s.done():
		case s.accept('Z') || s.accept('z'):
		case s.pos < len(text) && (text[s.pos] == '+' || text[s.pos] == '-'):
			sign := 1
			if text[s.pos] == '-' {
				sign = -1
			}
			s.pos++
			oh, ok := s.digits(2)
			if !ok {
				return time.Time{}, ErrInvalid
			}
			s.accept(':')
			om := 0
			if !s.done() {
				if om, ok = s.digits(2); !ok {
					return time.Time{}, ErrInvalid
				}
			}
			if oh > 23 || om > 59 {
				return time.Time{}, ErrInvalid
			}
			offset = sign * (oh*60 + om)
		default:
			return time.Time{}, ErrInvalid
		}
	}
	if !s.done() {
		return time.Time{}, ErrInvalid
	}
	t := time.Date(year, time.Month(month), day, hour, minute, second, millis*int(time.Millisecond), time.UTC)
	return t.Add(-time.Duration(offset) * time.Minute), nil
}

// Format formats t in UTC as YYYY-MM-DDThh:mm:ss.mmm+00:00.
func Format(t time.Time) string {
	return t.UTC().Format("2006-01-02T15:04:05.000") + "+00:00"
}
