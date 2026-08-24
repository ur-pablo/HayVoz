import Foundation
import SafariServices

private let appGroup = "group.com.urpablo.hayvoz"
private let maxChunkBytes = 384 * 1024
private let maxChunkCount = 16_384

final class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        let response = NSExtensionItem()
        do {
            guard
                let item = context.inputItems.first as? NSExtensionItem,
                let userInfo = item.userInfo as? [String: Any],
                let message = userInfo[SFExtensionMessageKey] as? [String: Any]
            else {
                throw BridgeError.invalidMessage
            }
            response.userInfo = [SFExtensionMessageKey: try handle(message)]
        } catch {
            response.userInfo = [
                SFExtensionMessageKey: [
                    "ok": false,
                    "status": "error",
                    "error": "El puente nativo de Safari rechazó el mensaje."
                ]
            ]
        }
        context.completeRequest(returningItems: [response], completionHandler: nil)
    }

    private func handle(_ message: [String: Any]) throws -> [String: Any] {
        guard let type = message["type"] as? String else {
            throw BridgeError.invalidMessage
        }
        if type == "ping" {
            return ["ok": true, "status": "ready"]
        }
        guard
            let rawID = message["capture_id"] as? String,
            let identifier = UUID(uuidString: rawID),
            identifier.uuidString.lowercased() == rawID.lowercased()
        else {
            throw BridgeError.invalidCapture
        }
        let directory = try captureDirectory(identifier.uuidString.lowercased())
        switch type {
        case "start":
            return try start(message, directory: directory, captureID: rawID.lowercased())
        case "chunk":
            return try chunk(message, directory: directory)
        case "finish":
            return try finish(message, directory: directory)
        case "status":
            return try status(directory: directory)
        default:
            throw BridgeError.invalidMessage
        }
    }

    private func start(
        _ message: [String: Any],
        directory: URL,
        captureID: String
    ) throws -> [String: Any] {
        guard
            let title = message["title"] as? String,
            !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
            title.count <= 120,
            let mimeType = message["mime_type"] as? String,
            ["audio/webm", "audio/webm;codecs=opus", "audio/mp4"].contains(mimeType)
        else {
            throw BridgeError.invalidMessage
        }
        let metadata: [String: Any] = [
            "schema_version": 1,
            "capture_id": captureID,
            "title": title.trimmingCharacters(in: .whitespacesAndNewlines),
            "mime_type": mimeType
        ]
        let path = directory.appendingPathComponent("metadata.json")
        if FileManager.default.fileExists(atPath: path.path) {
            guard NSDictionary(dictionary: try readJSON(path)).isEqual(to: metadata) else {
                throw BridgeError.invalidMessage
            }
        } else {
            try writeJSON(metadata, to: path)
        }
        return ["ok": true, "status": "receiving"]
    }

    private func chunk(_ message: [String: Any], directory: URL) throws -> [String: Any] {
        guard
            FileManager.default.fileExists(
                atPath: directory.appendingPathComponent("metadata.json").path
            ),
            let sequence = message["sequence"] as? Int,
            sequence >= 0,
            sequence < maxChunkCount,
            let encoded = message["data"] as? String,
            let data = Data(base64Encoded: encoded),
            !data.isEmpty,
            data.count <= maxChunkBytes
        else {
            throw BridgeError.invalidChunk
        }
        let path = directory.appendingPathComponent(
            String(format: "chunk-%08d.bin", sequence)
        )
        if FileManager.default.fileExists(atPath: path.path) {
            guard try Data(contentsOf: path) == data else {
                throw BridgeError.invalidChunk
            }
        } else {
            try data.write(to: path, options: .atomic)
            try protect(path)
        }
        return ["ok": true, "status": "receiving", "sequence": sequence]
    }

    private func finish(_ message: [String: Any], directory: URL) throws -> [String: Any] {
        guard
            let chunkCount = message["chunk_count"] as? Int,
            chunkCount > 0,
            chunkCount <= maxChunkCount
        else {
            throw BridgeError.invalidChunk
        }
        for sequence in 0..<chunkCount {
            let path = directory.appendingPathComponent(
                String(format: "chunk-%08d.bin", sequence)
            )
            guard FileManager.default.fileExists(atPath: path.path) else {
                throw BridgeError.invalidChunk
            }
        }
        try writeJSON(
            ["schema_version": 1, "chunk_count": chunkCount],
            to: directory.appendingPathComponent("request.json")
        )
        return ["ok": true, "status": "queued"]
    }

    private func status(directory: URL) throws -> [String: Any] {
        let result = directory.appendingPathComponent("result.json")
        if FileManager.default.fileExists(atPath: result.path) {
            let value = try readJSON(result)
            var response: [String: Any] = [:]
            for key in ["ok", "status", "session_id", "segment_count", "error"] {
                if let item = value[key] {
                    response[key] = item
                }
            }
            return response
        }
        if FileManager.default.fileExists(
            atPath: directory.appendingPathComponent("processing.json").path
        ) {
            return ["ok": true, "status": "processing"]
        }
        if FileManager.default.fileExists(
            atPath: directory.appendingPathComponent("request.json").path
        ) {
            return ["ok": true, "status": "queued"]
        }
        return ["ok": false, "status": "unknown"]
    }

    private func captureDirectory(_ identifier: String) throws -> URL {
        guard let group = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroup
        ) else {
            throw BridgeError.appGroupUnavailable
        }
        let root = group.appendingPathComponent("browser-inbox", isDirectory: true)
        let directory = root.appendingPathComponent(identifier, isDirectory: true)
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700]
        )
        return directory
    }

    private func writeJSON(_ value: [String: Any], to path: URL) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted])
        try data.write(to: path, options: .atomic)
        try protect(path)
    }

    private func readJSON(_ path: URL) throws -> [String: Any] {
        let value = try JSONSerialization.jsonObject(with: Data(contentsOf: path))
        guard let result = value as? [String: Any] else {
            throw BridgeError.invalidMessage
        }
        return result
    }

    private func protect(_ path: URL) throws {
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o600],
            ofItemAtPath: path.path
        )
    }
}

private enum BridgeError: Error {
    case invalidMessage
    case invalidCapture
    case invalidChunk
    case appGroupUnavailable
}
