package se.chalmers.investmentgame.utils;

import android.util.Log;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

// Java implementation of https://gist.github.com/diewland/d51a5ac476f3f63b481c4679763e034f
public class SuUtil {
    private static final String TAG = "SU_UTIL";

    public static ArrayList<String> exec(String cmd) {
        ArrayList<String> commands = new ArrayList<>();
        commands.add(cmd);

        return exec(commands);
    }

    // https://stackoverflow.com/a/11311955/466693
    public static ArrayList<String> exec(List<String> commands) {
        Process proc;
        try {
            proc = Runtime.getRuntime().exec("su");
        } catch (Exception e) {
            ArrayList<String> result = new ArrayList<>();
            result.add(null);
            result.add(null);
            return result;
        }

        try {
            DataOutputStream os = new DataOutputStream(proc.getOutputStream());

            for (String cmd : commands) {
                os.writeBytes(cmd + "\n");
            }

            os.writeBytes("exit\n");
            os.flush();
            os.close();

            proc.waitFor();

            return extractOutput(proc);

        } catch (Exception e) {
            ArrayList<String> result = new ArrayList<>();
            result.add(null);
            result.add(null);

            return result;
        }
    }

    public static ArrayList<String> exec2(String cmd) {
        try {
            Process proc = Runtime.getRuntime().exec(new String[]{"su", "-c", cmd});
            proc.waitFor();

            return extractOutput(proc);
        } catch (Exception e) {
            ArrayList<String> result = new ArrayList<>();
            result.add(null);
            result.add(null);

            return result;
        }
    }

    private static ArrayList<String> extractOutput(Process proc) {
        StringBuilder o = new StringBuilder();
        StringBuilder e = new StringBuilder();

        try {
            BufferedReader stdInput =
                    new BufferedReader(new InputStreamReader(proc.getInputStream()));
            BufferedReader stdError =
                    new BufferedReader(new InputStreamReader(proc.getErrorStream()));

            String line;

            while ((line = stdInput.readLine()) != null) {
                o.append(line);
            }

            while ((line = stdError.readLine()) != null) {
                e.append(line);
            }

        } catch (Exception ex) {
            Log.e(TAG, "Error reading process output", ex);
        }

        String outStr = o.length() == 0 ? null : o.toString();
        String errStr = e.length() == 0 ? null : e.toString();

        Log.d(TAG, "[success] " + outStr);
        Log.d(TAG, "[error  ] " + errStr);

        ArrayList<String> result = new ArrayList<>();
        result.add(outStr);
        result.add(errStr);

        return result;
    }
}