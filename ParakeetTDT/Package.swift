// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "ParakeetTDT",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "ParakeetTDT",
            targets: ["ParakeetTDT"])
    ],
    dependencies: [
        .package(url: "https://github.com/pvieito/PythonKit.git", branch: "master")
    ],
    targets: [
        .executableTarget(
            name: "ParakeetTDT",
            dependencies: ["PythonKit"],
            path: "Sources"),
        .testTarget(
            name: "ParakeetTDTTests",
            dependencies: ["ParakeetTDT"],
            path: "Tests")
    ]
)
