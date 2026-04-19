/**
 * OpenClaw plugin entry for lutron-cli.
 *
 * Each tool maps to a `lutron` subcommand. We invoke the binary with an
 * argv array (never a shell string) and JSON.parse the stdout — the CLI
 * emits JSON on every command by design.
 */

import { execFile, execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

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
    name: "lutron_turn_off",
    label: "Turn Off",
    description: "Turn off a device by device_id, with an optional fade duration in seconds.",
    parameters: {
      type: "object",
      properties: {
        device_id: { type: "string", description: "Device id from lutron_devices" },
        fade: { type: "number", description: "Fade time in seconds" },
      },
      required: ["device_id"],
    },
    argv: (params) => {
      const args = ["off", String(params.device_id)];
      if (typeof params.fade === "number") args.push("--fade", String(params.fade));
      return args;
    },
  },
  {
    name: "lutron_away_status",
    label: "Smart Away Status",
    description: "Return current Smart Away state (Enabled/Disabled).",
    parameters: { type: "object", properties: {} },
    argv: () => ["away"],
  },
  {
    name: "lutron_away_on",
    label: "Enable Smart Away",
    description:
      "Enable Smart Away (simulates occupancy by cycling lights while away).",
    parameters: { type: "object", properties: {} },
    argv: () => ["away", "on"],
  },
  {
    name: "lutron_away_off",
    label: "Disable Smart Away",
    description: "Disable Smart Away.",
    parameters: { type: "object", properties: {} },
    argv: () => ["away", "off"],
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
  try {
    const out = execFileSync("which", ["lutron"], { encoding: "utf8" }).trim();
    if (out) return out;
  } catch {
    // not on PATH
  }
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
  "Install lutron-cli first: `pipx install lutron-cli`. See https://github.com/omarshahine/lutron-cli for setup.";

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
          const { stdout } = await execFileAsync(cliPath, args, {
            encoding: "utf8",
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
