Gson 2.14.0, official upstream https://github.com/google/gson.

Tag: gson-parent-2.14.0. Annotated tag object: 93c8c0cc7fa991833b8c4da0cee487d52f85b092. Commit: 3ff35d6269894901ab8006258395aafc4b9765cd.

- gson-2.14.0.jar: https://repo.maven.apache.org/maven2/com/google/code/gson/gson/2.14.0/gson-2.14.0.jar
- GSON-LICENSE: https://raw.githubusercontent.com/google/gson/gson-parent-2.14.0/gson/LICENSE

The jar and licence are unmodified. GSON-LICENSE contains the full Apache License 2.0 and the upstream Google Gson identification and copyright notice. The release repository tree and jar contain no separate NOTICE file. Keep the supplied licence and the jar's existing manifest and metadata when redistributing. The manifest reports Bundle-Version 2.14.0 and the matching source tag.

The demo uses APIs checked with javap on this jar. Strictness behavior was also checked against these version-matched sources:

- https://raw.githubusercontent.com/google/gson/gson-parent-2.14.0/gson/src/main/java/com/google/gson/JsonParser.java
- https://raw.githubusercontent.com/google/gson/gson-parent-2.14.0/gson/src/main/java/com/google/gson/stream/JsonReader.java

Error Prone annotations 2.48.0 are Gson's declared compile-time annotation dependency, verified in the jar's embedded Maven POM. They are included so javac -Xlint:all -Werror does not warn about missing InlineMe annotation methods. They are not needed on the demo's runtime classpath. This is the annotation jar only, not the Error Prone compiler or a compiler plugin.

- error_prone_annotations-2.48.0.jar: https://repo.maven.apache.org/maven2/com/google/errorprone/error_prone_annotations/2.48.0/error_prone_annotations-2.48.0.jar
- ERROR-PRONE-LICENSE: https://raw.githubusercontent.com/google/error-prone/v2.48.0/COPYING
- Source: https://github.com/google/error-prone/tree/v2.48.0
- Commit: 7cec0a04b56cd79e72461ad771e532f503f0b407

The annotation jar and its Apache License 2.0 text are unmodified. No separate NOTICE file is present in that release repository tree or jar.

