import Vapor

struct Health: Content {
    var ok: Bool
    var runtime: String
}

var env = try Environment.detect()
try LoggingSystem.bootstrap(from: &env)
let app = Application(env)
defer { app.shutdown() }

app.get("api", "health") { _ in
    Health(ok: true, runtime: "swift-vapor")
}
app.get { _ in
    Response(
        status: .ok,
        headers: ["Content-Type": "text/html; charset=utf-8"],
        body: .init(string: "<h1>Olares Swift Vapor starter</h1><p>/api/health</p>")
    )
}

let port = Environment.get("PORT").flatMap(Int.init) ?? 8080
app.http.server.configuration.hostname = "0.0.0.0"
app.http.server.configuration.port = port
try app.run()
