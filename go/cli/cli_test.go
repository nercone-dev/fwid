package cli_test

import (
	"bytes"
	"strings"
	"testing"

	"github.com/nercone-dev/fwid/go/cli"
)

func run(args []string, stdin string) (int, string, string) {
	var out, errOut bytes.Buffer
	status := cli.CLI{}.Run(args, strings.NewReader(stdin), &out, &errOut)
	return status, out.String(), errOut.String()
}

func TestGenerateAndInspect(t *testing.T) {
	status, out, _ := run([]string{"g", "-t", "2024-01-01T00:00:00Z", "-b", "256", "-f", "compact", "-n", "3"}, "")
	lines := strings.Split(strings.TrimSpace(out), "\n")
	if status != 0 || len(lines) != 3 {
		t.Fatalf("status %d, lines %q", status, lines)
	}
	status, out, _ = run([]string{"i", lines[0]}, "")
	for _, want := range []string{
		"Format:     Compact Text\n",
		"Bits:       256 (timestamp 64, random 192)\n",
		"Timestamp:  2024-01-01T00:00:00.000+00:00 (725760000000 ms)\n",
	} {
		if status != 0 || !strings.Contains(out, want) {
			t.Errorf("missing %q in %q (status %d)", want, out, status)
		}
	}
	status, out, errOut := run([]string{"inspect"}, lines[1]+"  \n\nbogus\n"+lines[2]+"\n")
	if status != 1 || !strings.HasPrefix(errOut, "fwid: bogus: ") || strings.Count(out, "Format:") != 2 {
		t.Errorf("stdin: status %d, out %q, err %q", status, out, errOut)
	}
}

func TestUsageErrors(t *testing.T) {
	for _, args := range [][]string{{}, {"x"}, {"g", "-b", "0"}, {"g", "-b", "x"}, {"g", "-f", "nope"}, {"g", "-t", "yesterday"}, {"g", "-n"}, {"g", "--zzz"}} {
		if status, _, _ := run(args, ""); status != 2 {
			t.Errorf("%v: status %d, want 2", args, status)
		}
	}
	if status, _, _ := run([]string{"g", "-b", "128"}, ""); status != 1 {
		t.Errorf("small bits: status %d, want 1", status)
	}
	if status, _, _ := run([]string{"-h"}, ""); status != 0 {
		t.Errorf("-h: status %d, want 0", status)
	}
}
