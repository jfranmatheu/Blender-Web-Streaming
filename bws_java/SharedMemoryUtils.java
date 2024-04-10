import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Paths;

public class SharedMemoryUtils {
    public static void writeToSharedMemory(String sharedMemoryName, byte[] data) throws IOException {
        ByteBuffer buffer = ByteBuffer.wrap(data);
        Files.write(Paths.get("\\\\.\\Global\\", sharedMemoryName), buffer.array());
    }
}
