// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "OlaresVaporStarter",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/vapor/vapor.git", from: "4.102.0"),
    ],
    targets: [
        .executableTarget(
            name: "App",
            dependencies: [
                .product(name: "Vapor", package: "vapor"),
            ],
            path: "Sources/App"
        ),
    ]
)
