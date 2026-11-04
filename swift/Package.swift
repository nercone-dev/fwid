// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "FWID",
    products: [
        .library(name: "FWID", targets: ["FWID"]),
        .executable(name: "fwid", targets: ["FWIDCLI"]),
    ],
    targets: [
        .target(name: "FWID"),
        .executableTarget(name: "FWIDCLI", dependencies: ["FWID"]),
        .testTarget(
            name: "FWIDTests",
            dependencies: ["FWID", "FWIDCLI"]
        ),
    ]
)
