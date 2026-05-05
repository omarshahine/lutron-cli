/**
 * OpenClaw plugin entry for lutron-cli.
 *
 * Each tool maps to a `lutron` subcommand. We invoke the binary with an
 * argv array (never a shell string) and JSON.parse the stdout — the CLI
 * emits JSON on every command by design.
 */

import { existsSync } from "node:fs";
import { runCli, whichBinary } from "./safe-shell.js";

interface PluginConfig {
  cliPath?: string;
  bridgeHost?: string;
}

interface TextContent {
  type: "text";
  text: string;
}

interface ToolDefinition {
  name: string;
  label: string;
  description: string;
  parameters: Record<string, unknown>;
  execute: (
    toolCallId: string,
    params: Record<string, unknown>,
    signal?: AbortSignal
  ) => Promise<{ content: TextContent[] }>;
}

interface ToolContext {
  config?: Record<string, unknown>;
  workspaceDir?: string;
  agentDir?: string;
}

type ToolFactory = (ctx: ToolContext) => ToolDefinition | ToolDefinition[] | null | undefined;

interface OpenClawContext {
  config?: PluginConfig;
  registerTool(toolOrFactory: ToolDefinition | ToolFactory): void;
}

interface ToolSpec {
  name: string;
  label: string;
  description: string;
  parameters: Record<string, unknown>;
  /** Build the argv (after any --host prefix) from params. */
  argv: (params: Record<string, unknown>) => string[];
}

const TOOLS: ToolSpec[] = [
  {
    name: "lutron_scenes",
    label: "List Scenes",
    description:
      "List all programmed scenes on the Lutron bridge. Returns an array of {scene_id, name}.",
    parameters: { type: "object", properties: {} },
    argv: () => ["scenes"],
  },
  {
    name: "lutron_activate_scene",
    label: "Activate Scene",
    description:
      "Activate a Lutron scene by its scene_id. Use lutron_scenes first to look up ids.",
    parameters: {
      type: "object",
      properties: {
        scene_id: { type: "string", description: "Scene id from lutron_scenes" },
      },
      required: ["scene_id"],
    },
    argv: (params) => ["scene", String(params.scene_id)],
  },
  {
    name: "lutron_devices",
    label: "List Devices",
    description:
      "List every device paired with the bridge (lights, switches, Picos, shades, occupancy sensors). Optionally filter by domain.",
    parameters: {
      type: "object",
      properties: {
        domain: {
          type: "string",
          enum: ["light", "switch", "fan", "cover", "sensor"],
          description: "Filter by device domain",
        },
      },
    },
    argv: (params) => {
      const args = ["devices"];
      if (params.domain) args.push("--domain", String(params.domain));
      return args;
    },
  },
  {
    name: "lutron_device_status",
    label: "Device Status",
    description: "Get the current state of a device by device_id.",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Device id from lutron_devices" },
      },
      required: ["device_id"],
    },
    argv: (params) => ["status", String(params.device_id)],
  },
  {
    name: "lutron_set_level",
    label: "Set Device Level",
    description:
      "Set a light, dimmer, or switch to a specific level 0-100. Use 0 to turn off, 100 to turn fully on, anything in between to dim. This is the single tool for on/off/dim — there is no separate 'turn on' or 'turn off'. When level is 0, this routes through the bridge's native turn_off call for a clean off (matching the CLI's `off` subcommand); non-zero levels route through set_value for dim-to-level semantics.",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Device id from lutron_devices" },
        level: {
          type: "number",
          description: "Level 0-100 (0 = off, 100 = full on)",
          minimum: 0,
          maximum: 100,
        },
        fade: { type: "number", description: "Fade time in seconds" },
      },
      required: ["device_id", "level"],
    },
    argv: (params) => {
      // Route level=0 through `off` for parity with the bridge's native
      // turn_off call. Fade semantics are preserved in both paths because
      // the `off` CLI subcommand also accepts --fade.
      const level = Number(params.level);
      if (level === 0) {
        const args = ["off", String(params.device_id)];
        if (typeof params.fade === "number") args.push("--fade", String(params.fade));
        return args;
      }
      const args = ["level", String(params.device_id), String(level)];
      if (typeof params.fade === "number") args.push("--fade", String(params.fade));
      return args;
    },
  },
  {
    name: "lutron_set_fan",
    label: "Set Fan Speed",
    description:
      "Set a Caseta fan controller to Off, Low, Medium, MediumHigh, or High.",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Fan device id from lutron_devices" },
        speed: {
          type: "string",
          enum: ["Off", "Low", "Medium", "MediumHigh", "High"],
          description: "Fan speed preset",
        },
      },
      required: ["device_id", "speed"],
    },
    argv: (params) => ["fan", String(params.device_id), String(params.speed)],
  },
  {
    name: "lutron_cover",
    label: "Control Shade / Blind",
    description:
      "Raise, lower, or stop a shade or blind. Optional tilt (0-100) for tiltable blinds.",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Cover device id from lutron_devices" },
        action: {
          type: "string",
          enum: ["up", "down", "stop"],
          description: "Raise, lower, or stop the cover",
        },
        tilt: { type: "number", description: "Tilt 0-100 (tiltable blinds only)" },
      },
      required: ["device_id", "action"],
    },
    argv: (params) => {
      const args = ["cover", String(params.device_id), String(params.action)];
      if (typeof params.tilt === "number") args.push("--tilt", String(params.tilt));
      return args;
    },
  },
  {
    name: "lutron_warm_dim",
    label: "Set Warm Dim",
    description:
      "Set warm-dim level on a warm-dim-capable bulb. Dims warmer as level drops (candle-style).",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Warm-dim bulb device id" },
        level: { type: "number", description: "Level 0-100" },
        fade: { type: "number", description: "Fade time in seconds" },
        disable: {
          type: "boolean",
          description: "Disable warm-dim mode while still setting the level",
        },
      },
      required: ["device_id", "level"],
    },
    argv: (params) => {
      const args = ["warm", String(params.device_id), String(params.level)];
      if (typeof params.fade === "number") args.push("--fade", String(params.fade));
      if (params.disable === true) args.push("--disable");
      return args;
    },
  },
  {
    name: "lutron_buttons",
    label: "List Buttons",
    description:
      "List Pico / keypad buttons. Optionally filter by parent device. Returns button ids for lutron_tap.",
    parameters: {
      type: "object",
      properties: {
        device_id: {
          type: "string",
          description: "Filter to buttons on a specific Pico/keypad",
        },
      },
    },
    argv: (params) => {
      const args = ["buttons"];
      if (params.device_id) args.push("--device", String(params.device_id));
      return args;
    },
  },
  {
    name: "lutron_tap",
    label: "Tap Button",
    description:
      "Simulate a Pico or keypad button press by button_id. Use lutron_buttons to look up ids.",
    parameters: {
      type: "object",
      properties: {
        button_id: { type: "string", description: "Button id from lutron_buttons" },
      },
      required: ["button_id"],
    },
    argv: (params) => ["tap", String(params.button_id)],
  },
  {
    name: "lutron_battery",
    label: "Battery Status",
    description:
      "Get battery status for one device, or scan all battery-powered devices when device_id is omitted.",
    parameters: {
      type: "object",
      properties: {
        device_id: {
          type: "string",
          description: "Optional device id; omit to scan all battery-powered devices",
        },
      },
    },
    argv: (params) => {
      const args = ["battery"];
      if (params.device_id) args.push(String(params.device_id));
      return args;
    },
  },
  {
    name: "lutron_smart_away",
    label: "Smart Away",
    description:
      "Check, enable, or disable Smart Away (vacation mode that simulates occupancy by cycling lights). Pass action: 'status' to check current state (default), 'on' to enable, 'off' to disable.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: ["status", "on", "off"],
          description: "What to do: check status (default), enable, or disable",
        },
      },
    },
    argv: (params) => {
      const action = typeof params.action === "string" ? params.action : "status";
      if (action === "on") return ["away", "on"];
      if (action === "off") return ["away", "off"];
      return ["away"]; // status
    },
  },
  {
    name: "lutron_areas",
    label: "List Areas",
    description: "List rooms/areas configured on the bridge.",
    parameters: { type: "object", properties: {} },
    argv: () => ["areas"],
  },
  {
    name: "lutron_occupancy",
    label: "Occupancy Status",
    description: "List occupancy groups with their current Occupied/Unoccupied status.",
    parameters: { type: "object", properties: {} },
    argv: () => ["occupancy"],
  },
  {
    name: "lutron_all_off",
    label: "All Off",
    description:
      "Panic switch: turn off every controllable device (lights, switches, fans, covers). Pass `area` to limit to one room, `exclude` (comma-separated device ids) to spare specific devices, and `fade` seconds for a graceful dim-down. Returns the list of affected device ids.",
    parameters: {
      type: "object",
      properties: {
        area: {
          type: "string",
          description: "Area (room) name — limits the sweep to that area only",
        },
        fade: { type: "number", description: "Fade time in seconds" },
        exclude: {
          type: "string",
          description: "Comma-separated device ids to skip (e.g. '5,12')",
        },
      },
    },
    argv: (params) => {
      const args = ["all", "off"];
      if (params.area) args.push("--area", String(params.area));
      if (typeof params.fade === "number") args.push("--fade", String(params.fade));
      if (params.exclude) args.push("--exclude", String(params.exclude));
      return args;
    },
  },
  {
    name: "lutron_info",
    label: "Bridge Info",
    description:
      "Report bridge connection state, device/scene/area counts, and CLI/library versions. Use to sanity-check the connection or surface a quick health summary.",
    parameters: { type: "object", properties: {} },
    argv: () => ["info"],
  },
  {
    name: "lutron_export",
    label: "Export Bridge State",
    description:
      "Return a full JSON snapshot of areas, devices, scenes, occupancy groups, and buttons. Useful for backup, diffing after a config change, or seeding home-automation logic.",
    parameters: { type: "object", properties: {} },
    argv: () => ["export"],
  },
];

/**
 * Resolve the lutron binary path, in priority order:
 * 1. Plugin config cliPath (if file exists)
 * 2. LUTRON_CLI_PATH env var
 * 3. `which lutron` on PATH
 */
function resolveCliPath(config?: PluginConfig): string {
  if (config?.cliPath && existsSync(config.cliPath)) {
    return config.cliPath;
  }
  const envPath = process.env.LUTRON_CLI_PATH;
  if (envPath && existsSync(envPath)) {
    return envPath;
  }
  const onPath = whichBinary("lutron");
  if (onPath) return onPath;
  // Last resort: rely on PATH at exec time — Node will raise ENOENT with a
  // clear message, which we turn into installation instructions below.
  return config?.cliPath || "lutron";
}

function toTextResult(obj: unknown): { content: TextContent[] } {
  return {
    content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
  };
}

function errorResult(message: string): { content: TextContent[] } {
  return toTextResult({ success: false, error: message });
}

const INSTALL_HINT =
  "Install lutron-cli first: `pipx install git+https://github.com/omarshahine/lutron-cli`. See https://github.com/omarshahine/lutron-cli for setup.";

export default function activate(context: OpenClawContext): void {
  const config = context.config;
  const cliPath = resolveCliPath(config);
  const hostArgs = config?.bridgeHost ? ["--host", config.bridgeHost] : [];

  for (const spec of TOOLS) {
    context.registerTool((_ctx: ToolContext): ToolDefinition => ({
      name: spec.name,
      label: spec.label,
      description: spec.description,
      parameters: spec.parameters,

      async execute(_toolCallId, params) {
        const args = [...hostArgs, ...spec.argv(params)];
        try {
          const { stdout } = await runCli(cliPath, args, {
            timeout: 30_000,
            maxBuffer: 2 * 1024 * 1024,
          });
          try {
            return toTextResult(JSON.parse(stdout));
          } catch {
            return toTextResult({ output: stdout.trim() });
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          if (msg.includes("ENOENT") || msg.includes("not found")) {
            return errorResult(`${INSTALL_HINT} (tried: ${cliPath})`);
          }
          const stderr =
            err && typeof err === "object" && "stderr" in err
              ? String((err as { stderr: unknown }).stderr).trim()
              : "";
          return errorResult(stderr ? `${msg}\n\nstderr: ${stderr}` : msg);
        }
      },
    }));
  }
}
