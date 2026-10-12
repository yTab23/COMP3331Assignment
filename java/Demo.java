import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class Demo {
    private Demo() {}

    private static final class Hooks implements StudentTools.Progress, StudentTools.WaitStop {
        private final int cancelAfter;
        private int done;

        private Hooks(int cancelAfter) {
            this.cancelAfter = cancelAfter;
        }

        @Override
        public void update(int completed, int total) {
            done = completed;
            System.err.println("progress " + done + "/" + total);
        }

        @Override
        public boolean await(long delayMillis) throws InterruptedException {
            if (cancelAfter >= 0 && done >= cancelAfter) {
                return true;
            }
            Thread.sleep(delayMillis);
            return false;
        }
    }

    private static int integerOption(String text, int maximum) {
        if (!text.matches("[0-9]{1,5}")) {
            throw new IllegalArgumentException("Invalid demo option");
        }
        int value = Integer.parseInt(text);
        if (value > maximum) {
            throw new IllegalArgumentException("Invalid demo option");
        }
        return value;
    }

    private static int run(String[] args) {
        int delayMillis;
        int cancelAfter;
        try {
            if (args.length < 3 || args.length > 5
                    || (!args[1].equals("quick") && !args[1].equals("history")
                        && !args[1].equals("analysis"))
                    || (args.length > 3 && !args[1].equals("analysis"))) {
                throw new IllegalArgumentException("Invalid demo arguments");
            }
            delayMillis = args.length > 3 ? integerOption(args[3], 60000) : 0;
            cancelAfter = args.length > 4 ? integerOption(args[4], 1000) : -1;
        } catch (IllegalArgumentException exception) {
            System.err.println("Usage: Demo DATASET quick|history|analysis 'ARGS_JSON' [DELAY_MS [CANCEL_AFTER]]");
            return 64;
        }
        StudentTools tools;
        try {
            Path path = Path.of(args[0]);
            if (Files.size(path) > 1024 * 1024) {
                throw new IllegalArgumentException("Dataset exceeds 1 MiB");
            }
            tools = new StudentTools(StudentTools.parseJson(Files.readString(path, StandardCharsets.UTF_8)));
        } catch (IOException | JsonParseException | IllegalArgumentException exception) {
            System.err.println("Invalid or unreadable dataset (maximum 1 MiB)");
            return 1;
        }
        JsonElement arguments;
        try {
            arguments = StudentTools.parseJson(args[2]);
        } catch (IOException | JsonParseException exception) {
            System.err.println("Invalid JSON arguments");
            return 4;
        }
        try {
            Hooks hooks = new Hooks(cancelAfter);
            JsonObject result = switch (args[1]) {
                case "quick" -> tools.getReading(arguments);
                case "history" -> tools.getHistory(arguments);
                case "analysis" -> tools.analyseReadings(arguments, delayMillis, hooks, hooks);
                default -> throw new IllegalStateException("Unexpected demo mode");
            };
            System.out.println(result);
            return System.out.checkError() ? 1 : 0;
        } catch (StudentTools.InvalidArguments exception) {
            System.err.println(exception.getMessage());
            return 2;
        } catch (StudentTools.Cancelled exception) {
            System.err.println("Cancelled");
            return 3;
        } catch (ArithmeticException exception) {
            System.err.println("Analysis failed: temperature sum is not finite");
            return 1;
        }
    }

    public static void main(String[] args) {
        System.exit(run(args));
    }
}
