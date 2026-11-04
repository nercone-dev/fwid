// Command fwid generates and inspects FWIDs.
package main

import (
	"os"

	"github.com/nercone-dev/fwid/go/cli"
)

func main() {
	os.Exit(cli.CLI{}.Run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}
