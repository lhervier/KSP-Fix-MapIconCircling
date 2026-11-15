"""Plays the protocol of "Checking the culprit": the map view centred on the Mun, where PoseB is landed, while the
active vessel orbits it; the time warp is raised step by step, and the icon of PoseB should stay at its place.

It drives KSP through KSP-Util-MCPServer, a mod that answers HTTP requests on 127.0.0.1, and needs nothing but
Python 3: no AI, no package to install. Start KSP with KSP-Util-MCPServer installed, copy map-icon-circling.sfs into a
sandbox game, wait for the main menu, then run:

    python run-circling.py --folder <your sandbox game> --out out

It loads the save, opens the map view centred on the Mun, then, at each time warp rate in turn (1x, 100x, 1,000x and
10,000x by default), reads over a few hundred rendered frames how far the icon of PoseB is drawn from the place its
latitude, longitude and altitude give it on the Mun, and takes a screenshot. It goes back to 1x, prints a list of
checks, each PASS or FAIL, and exits with 0 when all pass, 1 otherwise. The checks marked (fix) are what the mod
promises: they fail without it. KSP is left running at the end.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

URL = None
LANDED = "PoseB"
BODY = "Mun"


def call(tool, **args):
    """Calls one tool of KSP-Util-MCPServer and returns its answer, decoded from JSON when it is JSON."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    request = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.loads(response.read())["result"]
    text = result["content"][0].get("text", "") if result["content"] else ""
    if result.get("isError"):
        raise RuntimeError(tool + ": " + text)
    try:
        return json.loads(text)
    except ValueError:
        return text


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


def landed_vessel():
    """The entry of PoseB in list_vessels."""
    for vessel in call("list_vessels"):
        if vessel["name"] == LANDED:
            return vessel
    raise RuntimeError("no vessel named %s: is the save the right one?" % LANDED)


def main():
    global URL
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", required=True, help="the sandbox game under saves/ the save was copied into")
    parser.add_argument("--save", default="map-icon-circling", help="the save, without .sfs")
    parser.add_argument("--rates", default="0,4,5,6",
                        help="the time warp rates to play, as indexes into KSP's rates (0 = 1x, 4 = 100x, "
                             "5 = 1,000x, 6 = 10,000x, 7 = 100,000x), comma separated")
    parser.add_argument("--distance", type=float, default=60.0,
                        help="the distance of the map's camera from the Mun, in units of the map (6 km each)")
    parser.add_argument("--frames", type=int, default=300, help="how many rendered frames to read at each rate")
    parser.add_argument("--settle", type=float, default=1.0, help="seconds to wait at each rate before reading")
    parser.add_argument("--tolerance", type=float, default=3.0,
                        help="the largest gap, in pixels, between the icon and its place that counts as at its place")
    parser.add_argument("--out", default="out", help="where the screenshots go")
    parser.add_argument("--port", type=int, default=8770, help="the port of KSP-Util-MCPServer")
    options = parser.parse_args()
    URL = "http://127.0.0.1:%d/mcp/" % options.port
    os.makedirs(options.out, exist_ok=True)
    rates = [int(r) for r in options.rates.split(",")]
    checks = []

    def check(fix, ok, text):
        checks.append((ok, ("(fix) " if fix else "") + text))

    if call("get_state")["scene"] == "MAINMENU":
        call("open_game", folder=options.folder)
    state = call("load_save", folder=options.folder, save=options.save)
    log("loaded: %s, %s around the %s" % (state["vessel"]["name"], state["vessel"]["situation"],
                                          state["vessel"]["body"]))
    landed = landed_vessel()
    check(False, landed["situation"] == "LANDED" and not landed["loaded"],
          "%s is landed and not loaded" % LANDED)

    # 1. The map view, centred on the Mun: the Mun stays still on screen, the icon of PoseB on it.
    call("map_view", focus=BODY, distance=options.distance)
    time.sleep(2)

    # 2. Each rate in turn: how far the icon is drawn from its place, frame after frame.
    try:
        for index in rates:
            warp = call("set_warp", rate_index=index)
            rate = warp["rate"]
            time.sleep(options.settle)
            reading = call("read_map_icon", vessel=LANDED, frames=options.frames)
            call("screenshot", path=os.path.abspath(os.path.join(options.out, "circling-x%g.png" % rate)),
                 return_image=False)
            shown = reading["shownFrames"]
            gap = reading["gapMax"]
            log("%gx: icon shown in %d of %d frames, gap mean %s px, largest %s px" % (
                rate, shown, reading["frames"], reading["gapMean"], gap))
            measured = shown >= reading["frames"] // 2
            check(rate >= 1000, measured and gap is not None and gap <= options.tolerance,
                  "at %gx, the icon of %s stays at its place (%s px at most)" % (
                      rate, LANDED, gap if measured else "icon hidden, not measured"))
    finally:
        call("set_warp", rate_index=0)

    print()
    for ok, text in checks:
        print("PASS" if ok else "FAIL", text)
    passed = sum(1 for ok, _ in checks if ok)
    print("%d of %d checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
