// Package cli implements the fwid command line.
package cli

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"

	fwid "github.com/nercone-dev/fwid/ports/go"
	"github.com/nercone-dev/fwid/ports/go/iso8601"
)

const usage = "usage: fwid [-h] COMMAND ..."

const help = `usage: fwid [-h] COMMAND ...

Generate and inspect FWIDs (FourWord Identifiers).

commands:
  generate, g   generate FWIDs
  inspect, i    show the contents of FWIDs

options:
  -h, --help    show this help message and exit

generate options:
  -b, --bits BITS       total bit length, a multiple of 32
                        (default: the smallest that fits the timestamp)
  -f, --format FORMAT   standard, readable or compact (default: standard)
  -n, --count COUNT     number of FWIDs to generate (default: 1)
  -t, --time DATETIME   ISO 8601 timestamp to embed; naive values are UTC
                        (default: now)

inspect arguments:
  FWID                  FWIDs in any text format; read from standard input,
                        one per line, if omitted or '-'
`

// CLI is the fwid command line.
type CLI struct{}

type usageError string

func (e usageError) Error() string { return string(e) }

type command struct {
	name   string // "help", "generate" or "inspect"
	bits   int
	format fwid.Format
	count  int
	time   time.Time
	ids    []string
}

func positive(text string) (int, error) {
	value, err := strconv.Atoi(text)
	if err != nil {
		return 0, usageError(fmt.Sprintf("invalid integer: %q", text))
	}
	if value < 1 {
		return 0, usageError("must be 1 or greater")
	}
	return value, nil
}

func parseFormat(text string) (fwid.Format, error) {
	switch text {
	case "standard":
		return fwid.StandardText, nil
	case "readable":
		return fwid.ReadableText, nil
	case "compact":
		return fwid.CompactText, nil
	}
	return 0, usageError(fmt.Sprintf("invalid choice: %q (choose from compact, readable, standard)", text))
}

func parseTime(text string) (time.Time, error) {
	t, err := iso8601.Parse(text)
	if err != nil {
		return t, usageError(fmt.Sprintf("invalid ISO 8601 datetime: %q", text))
	}
	return t, nil
}

// args is the remaining command line.
type args []string

func (a *args) next() (string, bool) {
	if len(*a) == 0 {
		return "", false
	}
	arg := (*a)[0]
	*a = (*a)[1:]
	return arg, true
}

// value matches -bVALUE, --bits=VALUE, -b VALUE and --bits VALUE. ok is false
// if arg is not this option.
func (a *args) value(arg, short, long string) (value string, ok bool, err error) {
	switch {
	case strings.HasPrefix(arg, "--"+long+"="):
		return arg[len(long)+3:], true, nil
	case len(arg) > 2 && strings.HasPrefix(arg, "-"+short) && !strings.HasPrefix(arg, "--"):
		return arg[2:], true, nil
	case arg == "--"+long || arg == "-"+short:
		value, found := a.next()
		if !found {
			return "", true, usageError(fmt.Sprintf("argument -%s/--%s: expected one argument", short, long))
		}
		return value, true, nil
	}
	return "", false, nil
}

func option[T any](name string, parse func(string) (T, error), text string) (T, error) {
	v, err := parse(text)
	var ue usageError
	if errors.As(err, &ue) {
		err = usageError(fmt.Sprintf("argument %s: %s", name, ue))
	}
	return v, err
}

func parse(rest args) (command, error) {
	name, ok := rest.next()
	if !ok {
		return command{}, usageError("the following arguments are required: COMMAND")
	}
	switch name {
	case "-h", "--help":
		return command{name: "help"}, nil
	case "generate", "g":
		c := command{name: "generate", format: fwid.StandardText, count: 1}
		for {
			arg, ok := rest.next()
			if !ok {
				return c, nil
			}
			if arg == "-h" || arg == "--help" {
				return command{name: "help"}, nil
			}
			var err error
			if v, ok, e := rest.value(arg, "b", "bits"); ok {
				if e != nil {
					return c, e
				}
				c.bits, err = option("-b/--bits", positive, v)
			} else if v, ok, e := rest.value(arg, "f", "format"); ok {
				if e != nil {
					return c, e
				}
				c.format, err = option("-f/--format", parseFormat, v)
			} else if v, ok, e := rest.value(arg, "n", "count"); ok {
				if e != nil {
					return c, e
				}
				c.count, err = option("-n/--count", positive, v)
			} else if v, ok, e := rest.value(arg, "t", "time"); ok {
				if e != nil {
					return c, e
				}
				c.time, err = option("-t/--time", parseTime, v)
			} else {
				err = usageError("unrecognized arguments: " + arg)
			}
			if err != nil {
				return c, err
			}
		}
	case "inspect", "i":
		c := command{name: "inspect"}
		optionsDone := false
		for {
			arg, ok := rest.next()
			if !ok {
				return c, nil
			}
			switch {
			case !optionsDone && arg == "--":
				optionsDone = true
			case !optionsDone && (arg == "-h" || arg == "--help"):
				return command{name: "help"}, nil
			case !optionsDone && len(arg) > 1 && arg[0] == '-':
				return c, usageError("unrecognized arguments: " + arg)
			default:
				c.ids = append(c.ids, arg)
			}
		}
	}
	return command{}, usageError(fmt.Sprintf("argument COMMAND: invalid choice: %q (choose from generate, g, inspect, i)", name))
}

func describe(out io.Writer, text string) error {
	format, id, err := fwid.Parse(text)
	if err != nil {
		return err
	}
	ms, err := id.TimestampMS()
	if err != nil {
		return err
	}
	t, err := id.Timestamp()
	if err != nil {
		return err
	}
	_, err = fmt.Fprintf(out, "Format:     %s\nBits:       %d (timestamp %d, random %d)\nTimestamp:  %s (%d ms)\nHex:        %x\nStandard:   %s\nReadable:   %s\nCompact:    %s\n",
		format.Name(), id.Bits(), id.BitsTimestamp(), id.BitsRandom(), iso8601.Format(t), ms, id.Bytes(),
		id.StandardText(), id.ReadableText(), id.CompactText())
	return err
}

// ioError marks failures of the output stream, which are not worth a message.
type ioError struct{ error }

func (CLI) generate(c command, out io.Writer) error {
	for i := 0; i < c.count; i++ {
		id, err := fwid.Generate(c.bits, c.time)
		if err != nil {
			return err
		}
		text, err := id.Text(c.format)
		if err != nil {
			return err
		}
		if _, err := fmt.Fprintln(out, text); err != nil {
			return ioError{err}
		}
	}
	return nil
}

func (CLI) inspect(c command, stdin io.Reader, out, errOut io.Writer) (int, error) {
	texts := c.ids
	if len(texts) == 0 || (len(texts) == 1 && texts[0] == "-") {
		texts = nil
		scanner := bufio.NewScanner(stdin)
		scanner.Buffer(nil, 1<<30)
		for scanner.Scan() {
			if line := strings.TrimSpace(scanner.Text()); line != "" {
				texts = append(texts, line)
			}
		}
		if err := scanner.Err(); err != nil {
			return 1, err
		}
	}
	status := 0
	for i, text := range texts {
		if i > 0 {
			if _, err := fmt.Fprintln(out); err != nil {
				return 1, ioError{err}
			}
		}
		if err := describe(out, text); err != nil {
			fmt.Fprintf(errOut, "fwid: %s: %v\n", text, err)
			status = 1
		}
	}
	return status, nil
}

// Run runs the command line with args (without the program name) and returns the exit status.
func (cli CLI) Run(argv []string, stdin io.Reader, stdout, stderr io.Writer) int {
	c, err := parse(args(argv))
	if err != nil {
		fmt.Fprintf(stderr, "%s\nfwid: error: %v\n", usage, err)
		return 2
	}
	out := bufio.NewWriter(stdout)
	status := 0
	switch c.name {
	case "help":
		out.WriteString(help)
	case "generate":
		err = cli.generate(c, out)
	case "inspect":
		status, err = cli.inspect(c, stdin, out, stderr)
	}
	if flushErr := out.Flush(); err == nil && flushErr != nil {
		err = ioError{flushErr}
	}
	if err != nil {
		var ie ioError
		if !errors.As(err, &ie) {
			fmt.Fprintf(stderr, "fwid: %v\n", err)
		}
		return 1
	}
	return status
}
