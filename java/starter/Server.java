public final class Server {
    private Server() {}

    public static void main(String[] args) {
        Starter.Options options;
        try {
            options = Starter.options(args, true);
        } catch (IllegalArgumentException exception) {
            System.err.println("Invalid launch option; use --help");
            System.exit(2);
            return;
        }
        // Student: load support/data/readings.json and support/schemas/tools.json.
        // Construct StudentTools once from the parsed dataset. Bind a TCP listener
        // to 127.0.0.1 at options.port(). Own accept/read/write, HTTP framing,
        // method/tool dispatch, JSON/SSE responses, reuse and cleanup.
        // Convert options.analysisDelay() seconds to milliseconds for analysis.
        // Own per-connection work and stop state; connect progress and wait/stop
        // hooks to that call's transport and stop computation on disconnect.
        System.err.println("starter-not-implemented: server networking and dispatch");
        System.exit(1);
    }
}
