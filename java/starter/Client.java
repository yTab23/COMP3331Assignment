import com.google.gson.JsonObject;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

public final class Client {
    private Client() {}

    public static void main(String[] args) throws IOException {
        Starter.Options options;
        try {
            options = Starter.options(args, false);
        } catch (IllegalArgumentException exception) {
            System.err.println("Invalid launch option; use --help");
            System.exit(2);
            return;
        }
        try (BufferedReader input = new BufferedReader(
                new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = input.readLine()) != null) {
                JsonObject command = StudentTools.parseJson(line).getAsJsonObject();
                // Student: dispatch discover/list/call/cancel/wait using command
                // and options. Own ids, tokens, sockets, HTTP sending/decoding,
                // SSE parsing, response matching, connection reuse, active calls,
                // deadlines and cancellation. At EOF drain calls and close sockets.
                // Report started/idle/success only after implementing that work.
                JsonObject event = new JsonObject();
                event.addProperty("event", "input_error");
                event.addProperty("message", "starter-not-implemented");
                Starter.output(event);
            }
        }
        System.err.println("starter-not-implemented: client networking and EOF cleanup");
        System.exit(1);
    }
}
