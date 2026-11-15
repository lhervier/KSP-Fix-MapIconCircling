using UnityEngine;

namespace com.github.lhervier.ksp.fix.mapiconcircling
{
    /// <summary>
    /// Reads the settings and logs the version, once, when KSP starts. The fix itself runs in flight, in
    /// <see cref="LandedCoMAfterShift"/>.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Instantly, true)]
    public class KSPFixMapIconCircling : MonoBehaviour
    {
        private void Start()
        {
            Settings.Load();
            Log.Info($"Version {typeof(KSPFixMapIconCircling).Assembly.GetName().Version}, " +
                $"fixLandedCoMAfterShift {Settings.FixLandedCoMAfterShift}, log level {Log.Level}");
        }
    }
}
