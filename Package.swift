// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "HayVozSafariBridge",
    platforms: [.macOS(.v13)],
    products: [
        .library(
            name: "HayVozSafariBridge",
            targets: ["HayVozSafariBridge"]
        )
    ],
    targets: [
        .target(
            name: "HayVozSafariBridge",
            path: "extensions/safari"
        )
    ]
)
