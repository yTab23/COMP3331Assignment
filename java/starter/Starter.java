import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.io.IOException;

/** Editable launch and JSON helpers only. No transport or request lifecycle. */
public final class Starter {
    private Starter() {}

    /** Times are seconds. */
    public record Options(String host, int port, double timeout, double analysisDelay) {}

    public static Options options(String[] args, boolean server) {
        String host = "127.0.0.1";
        int port = 51000;
        double timeout = 30;
        double delay = 0.5;
        for (int i = 0; i < args.length; i++) {
            String key = args[i];
            if (key.equals("--help")) {
                System.out.println(server
                        ? "Usage: Server [--port 51000] [--analysis-delay 0.5]"
                        : "Usage: Client [--host 127.0.0.1] [--port 51000] [--timeout 30]");
                System.out.println("Times are seconds. --help prints this message.");
                System.exit(0);
            }
            if (++i == args.length) {
                throw new IllegalArgumentException("Missing option value; use --help");
            }
            String value = args[i];
            if (!server && key.equals("--host")) {
                host = value;
                continue;
            }
            double number = Double.parseDouble(value);
            if (!Double.isFinite(number)) {
                throw new IllegalArgumentException("Expected a finite option value");
            }
            if (key.equals("--port") && number >= 1 && number <= 65535
                    && Math.floor(number) == number) {
                port = (int) number;
            } else if (server && key.equals("--analysis-delay") && number >= 0) {
                delay = number;
            } else if (!server && key.equals("--timeout") && number > 0) {
                timeout = number;
            } else {
                throw new IllegalArgumentException("Invalid launch option; use --help");
            }
        }
        return new Options(host, port, timeout, delay);
    }

    /** All application JSON output uses this lock, including flush.
     * The caller does not mutate value while it is being serialized. */
    public static synchronized void output(JsonElement value) throws IOException {
        System.out.println(value);
        System.out.flush();
        if (System.out.checkError()) {
            throw new IOException("JSON output failed");
        }
    }

    private static JsonObject envelope(JsonElement id) {
        JsonObject message = new JsonObject();
        message.addProperty("jsonrpc", "2.0");
        if (id != null) {
            message.add("id", id.deepCopy());
        }
        return message;
    }

    /** Constructors copy inputs, assuming valid ids, tokens and field objects.
     * Replaces params._meta; a null token omits progressToken. */
    public static JsonObject request(JsonElement id, String method,
            JsonObject params, JsonElement token) {
        JsonObject message = envelope(id);
        JsonObject body = params.deepCopy();
        JsonObject meta = new JsonObject();
        meta.addProperty("io.modelcontextprotocol/protocolVersion", "2026-07-28");
        meta.add("io.modelcontextprotocol/clientCapabilities", new JsonObject());
        if (token != null) {
            meta.add("progressToken", token.deepCopy());
        }
        body.add("_meta", meta);
        message.addProperty("method", method);
        message.add("params", body);
        return message;
    }

    /** Replaces fields.resultType; other result fields come from the caller. */
    public static JsonObject completed(JsonElement id, JsonObject fields) {
        JsonObject message = envelope(id);
        JsonObject result = fields.deepCopy();
        result.addProperty("resultType", "complete");
        message.add("result", result);
        return message;
    }

    /** null id omits id (unrecoverable request); null data omits error.data. */
    public static JsonObject error(JsonElement id, int code, String text, JsonElement data) {
        JsonObject message = envelope(id);
        JsonObject error = new JsonObject();
        error.addProperty("code", code);
        error.addProperty("message", text);
        if (data != null) {
            error.add("data", data.deepCopy());
        }
        message.add("error", error);
        return message;
    }

    /** total < 0 omits total. Notifications have no id. */
    public static JsonObject progress(JsonElement token, int done, int total) {
        JsonObject message = envelope(null);
        JsonObject params = new JsonObject();
        message.addProperty("method", "notifications/progress");
        params.add("progressToken", token.deepCopy());
        params.addProperty("progress", done);
        if (total >= 0) {
            params.addProperty("total", total);
        }
        message.add("params", params);
        return message;
    }
}
