import { spawnSync } from "node:child_process";
import process from "node:process";

const playwrightImage = "mcr.microsoft.com/playwright:v1.60.0-noble";
const updateSnapshots = process.argv.includes("--update-snapshots");
const testCommand = updateSnapshots
  ? "npm run test:vrt:container -- --update-snapshots"
  : "npm run test:vrt:container";

const result = spawnSync(
  "docker",
  [
    "run",
    "--rm",
    "--init",
    "--ipc=host",
    "--platform",
    "linux/amd64",
    "--env",
    "CI=1",
    "--volume",
    `${process.cwd()}:/work`,
    "--volume",
    "/work/node_modules",
    "--workdir",
    "/work",
    playwrightImage,
    "bash",
    "-lc",
    `npm ci && ${testCommand}`,
  ],
  { stdio: "inherit" },
);

if (result.error) {
  console.error(`DockerでVRTを実行できませんでした: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
