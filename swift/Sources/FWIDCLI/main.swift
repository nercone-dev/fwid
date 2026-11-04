import Foundation

let status = CLI.run(
    Array(CommandLine.arguments.dropFirst()),
    readLine: { Swift.readLine() },
    out: { FileHandle.standardOutput.write(Data($0.utf8)) },
    err: { FileHandle.standardError.write(Data($0.utf8)) }
)
exit(status)
