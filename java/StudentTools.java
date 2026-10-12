import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import com.google.gson.Strictness;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.io.IOException;
import java.io.StringReader;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Set;

/** Local business computation only. No transport, MCP envelope, or dispatch. */
public final class StudentTools {
    private final JsonObject dataset;

    /** Takes an independent copy. Arrays are already chronological in the fixture. */
    public StudentTools(JsonElement loadedDataset) {
        if (!loadedDataset.isJsonObject() || loadedDataset.getAsJsonObject().isEmpty()) {
            throw new IllegalArgumentException("Invalid dataset");
        }
        for (JsonElement records : loadedDataset.getAsJsonObject().asMap().values()) {
            if (!records.isJsonArray() || records.getAsJsonArray().isEmpty()) {
                throw new IllegalArgumentException("Invalid dataset readings");
            }
            for (JsonElement record : records.getAsJsonArray()) {
                JsonElement temperature = record.isJsonObject()
                        ? record.getAsJsonObject().get("temperature_c") : null;
                if (temperature == null || !temperature.isJsonPrimitive()
                        || !temperature.getAsJsonPrimitive().isNumber()
                        || !Double.isFinite(temperature.getAsDouble())) {
                    throw new IllegalArgumentException("Invalid dataset temperature");
                }
            }
        }
        dataset = loadedDataset.getAsJsonObject().deepCopy();
    }

    /** Exactly one RFC 8259 document, not Gson's default lenient parsing. */
    public static JsonElement parseJson(String text) throws IOException {
        try (JsonReader reader = new JsonReader(new StringReader(text))) {
            reader.setStrictness(Strictness.STRICT);
            reader.setNestingLimit(64);
            if (reader.peek() == JsonToken.END_DOCUMENT) {
                throw new JsonParseException("Empty JSON input");
            }
            JsonElement value = JsonParser.parseReader(reader);
            if (reader.peek() != JsonToken.END_DOCUMENT) {
                throw new JsonParseException("Trailing JSON input");
            }
            return value;
        }
    }

    public static final class InvalidArguments extends Exception {
        private static final long serialVersionUID = 1L;

        private InvalidArguments(String message) {
            super(message);
        }
    }

    public static final class Cancelled extends Exception {
        private static final long serialVersionUID = 1L;

        private Cancelled() {
            super("Cancelled");
        }

        private Cancelled(InterruptedException cause) {
            super("Cancelled", cause);
        }
    }

    @FunctionalInterface
    public interface Progress {
        void update(int done, int total);
    }

    /** Caller owns stop state and interruptible waiting, including delayMillis=0. */
    @FunctionalInterface
    public interface WaitStop {
        boolean await(long delayMillis) throws InterruptedException;
    }

    private record Station(String id, JsonArray records) {}

    private Station records(JsonElement arguments, Set<String> fields) throws InvalidArguments {
        if (!arguments.isJsonObject() || !arguments.getAsJsonObject().keySet().equals(fields)) {
            throw new InvalidArguments("Incorrect tool argument fields");
        }
        JsonElement station = arguments.getAsJsonObject().get("station_id");
        if (!station.isJsonPrimitive() || !station.getAsJsonPrimitive().isString()
                || !dataset.has(station.getAsString())) {
            throw new InvalidArguments("Unknown station_id");
        }
        return new Station(station.getAsString(), dataset.getAsJsonArray(station.getAsString()));
    }

    private static JsonObject resultFor(Station station) {
        JsonObject result = new JsonObject();
        result.addProperty("station_id", station.id());
        return result;
    }

    /** Arguments are borrowed; returned JSON is independent and caller-owned. */
    public JsonObject getReading(JsonElement arguments) throws InvalidArguments {
        Station station = records(arguments, Set.of("station_id"));
        JsonObject result = resultFor(station);
        result.add("reading", station.records().get(station.records().size() - 1).deepCopy());
        return result;
    }

    public JsonObject getHistory(JsonElement arguments) throws InvalidArguments {
        Station station = records(arguments, Set.of("station_id", "limit"));
        JsonElement value = arguments.getAsJsonObject().get("limit");
        if (!value.isJsonPrimitive() || !value.getAsJsonPrimitive().isNumber()) {
            throw new InvalidArguments("limit must be an integer from 1 to 1000");
        }
        double limit = value.getAsDouble();
        if (!Double.isFinite(limit) || limit < 1 || limit > 1000 || Math.floor(limit) != limit) {
            throw new InvalidArguments("limit must be an integer from 1 to 1000");
        }
        JsonArray history = new JsonArray();
        for (int i = Math.max(0, station.records().size() - (int) limit);
                i < station.records().size(); i++) {
            history.add(station.records().get(i).deepCopy());
        }
        JsonObject result = resultFor(station);
        result.add("readings", history);
        return result;
    }

    /** Hooks run synchronously. Stop is checked before each step and after the last.
     * Thread interruption is cancellation; the interrupt flag and cause are retained. */
    public JsonObject analyseReadings(JsonElement arguments, long stepDelayMillis,
            Progress progress, WaitStop stop) throws InvalidArguments, Cancelled {
        Station station = records(arguments, Set.of("station_id"));
        if (stepDelayMillis < 0 || progress == null || stop == null) {
            throw new IllegalArgumentException("Invalid analysis hooks or delay");
        }
        double total = 0.0;
        int done = 0;
        try {
            for (JsonElement record : station.records()) {
                if (stop.await(stepDelayMillis)) {
                    throw new Cancelled();
                }
                total += record.getAsJsonObject().get("temperature_c").getAsDouble();
                progress.update(++done, station.records().size());
            }
            if (stop.await(0)) {
                throw new Cancelled();
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new Cancelled(exception);
        }
        if (!Double.isFinite(total)) {
            throw new ArithmeticException("Temperature sum is not finite");
        }
        // Round the exact binary double, matching Python round(mean, 2).
        double mean = new BigDecimal(total / done).setScale(2, RoundingMode.HALF_EVEN).doubleValue();
        JsonObject result = resultFor(station);
        result.addProperty("count", done);
        result.addProperty("mean_temperature_c", mean);
        return result;
    }
}
