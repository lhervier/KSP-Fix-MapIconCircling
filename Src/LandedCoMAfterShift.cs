using System;
using System.Collections.Generic;
using UnityEngine;

namespace com.github.lhervier.ksp.fix.mapiconcircling
{
    /// <summary>
    /// In flight, after each floating origin shift long enough to make the game recompute the centre of mass of packed
    /// vessels, recomputes it for unloaded landed vessels from their shifted surface position, so that their centre of
    /// mass, hence their map icon, stays at their place.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class LandedCoMAfterShift : MonoBehaviour
    {
        private const int DebugEvery = 1000;

        /// <summary>Number of vessel corrections made since KSP started.</summary>
        public static long Corrections { get; private set; }

        private bool subscribed;

        private void Awake()
        {
            if (!Settings.FixLandedCoMAfterShift)
            {
                return;
            }
            // EventData.Add needs an instance method: a static one throws and registers nothing.
            GameEvents.onFloatingOriginShift.Add(OnFloatingOriginShift);
            subscribed = true;
        }

        private void OnDestroy()
        {
            if (subscribed)
            {
                GameEvents.onFloatingOriginShift.Remove(OnFloatingOriginShift);
            }
        }

        /// <summary>
        /// Puts back at their place the unloaded landed vessels that <c>FloatingOrigin.setOffset</c> just left off by
        /// the whole shift.
        /// </summary>
        private void OnFloatingOriginShift(Vector3d offset, Vector3d nonFrame)
        {
            try
            {
                // For a shift longer than sqrt(CoMRecalcOffsetMaxSqr), 10 km by default, setOffset calls
                // precalc.CalculatePhysicsStats() on every packed vessel instead of moving CoMD by the shift. For an
                // unloaded landed vessel, that call rebuilds CoMD from precalc.worldSurfacePos, which setOffset does
                // not move: CoMD stays in the frame before the shift. Below that length, setOffset moves CoMD itself,
                // which is right. KSP Community Fixes' FloatingOriginPerf keeps the same logic and fires the same event.
                FloatingOrigin floatingOrigin = FloatingOrigin.fetch;
                if (floatingOrigin == null || offset.sqrMagnitude <= floatingOrigin.CoMRecalcOffsetMaxSqr)
                {
                    return;
                }
                // What setOffset moved such a vessel by (its offsetNonKrakensbane).
                Vector3d shift = offset + nonFrame;
                List<Vessel> vessels = FlightGlobals.Vessels;
                for (int i = 0; i < vessels.Count; i++)
                {
                    Vessel vessel = vessels[i];
                    // A loaded vessel takes its CoM from its rigidbodies, already moved: nothing to fix.
                    if (vessel == null || vessel.state == Vessel.State.DEAD || vessel.loaded || !vessel.packed
                        || !vessel.LandedOrSplashed || vessel.precalc == null)
                    {
                        continue;
                    }
                    vessel.precalc.worldSurfacePos -= shift;
                    // Same formula as the game, now from the shifted surface position. The next physics step computes
                    // worldSurfacePos again from latitude and longitude, as it always does.
                    vessel.precalc.CalculatePhysicsStats();
                    Corrections++;
                    if (Log.IsDebugEnabled && Corrections % DebugEvery == 1)
                    {
                        Log.Debug($"Correction {Corrections}: {vessel.vesselName}, shift {offset.magnitude:F0} m");
                    }
                }
            }
            catch (Exception e)
            {
                Log.Error($"Could not put landed vessels back at their place after a floating origin shift: {e}");
            }
        }
    }
}
