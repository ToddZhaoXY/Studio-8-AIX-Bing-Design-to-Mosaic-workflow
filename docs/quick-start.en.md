# English quick start

The workbench UI and new build reports are in English. Source card text, your inputs, and existing reports stay in their original language.

## Set up

1. Use macOS or Linux with Python 3.9+. On Windows, run inside WSL2.
2. Install and sign in to [Codex CLI](https://developers.openai.com/codex/cli/) with your own account or provider.
3. Install Mosaic CLI using the [bundled setup guide](../.agents/skills/mosaic-gen-workflow/references/api-and-iteration-workflow.md). Run `mosaic login` and `mosaic status`. You need your own Mosaic access and may need a corporate network or VPN.

```sh
git clone https://github.com/ToddZhaoXY/Studio-8-AIX-Bing-Design-to-Mosaic-workflow.git
cd Studio-8-AIX-Bing-Design-to-Mosaic-workflow
python3 tools/mosaic-workbench/doctor.py
./start.sh
```

On macOS, you can also double-click **Start Mosaic Workbench.command**. The Library ZIP and complete workflow skill are included. No model or template generation runs during the default offline doctor check.

## Build

1. Filter the library, preview the original component, and select up to 50 entries.
2. Check the connections and choose an available Mosaic version.
3. Select **your** workspace and folder. No destination is selected automatically.
4. Set the template prefix and optional instructions, then choose **Build with Codex**.
5. Follow the queue and open **View report** or **History** to inspect results.

Codex reads the selected source and skill, inspects native Mosaic contracts, writes through controlled CLI tools, checks evidence, and reports differences. It does not hand authoring to Mosaic autopilot.

The default limit is 5 minutes per card with one repair. Repairs stay in one iteration. Failed or timed-out items keep saved work and the batch continues. Templates are not automatically published.

## Settings and reports

Use **Skill → Import ZIP → Activate** to update the workflow independently. Running tasks keep their original snapshot.

Optional personal settings belong in `workbench.local.json`, copied from [workbench.example.json](../workbench.example.json). Configure binary paths, a default destination, a compatible source ZIP, or the HTTPS asset base as needed. This file is ignored by Git. Never put passwords or tokens in it.

```sh
python3 tools/mosaic-workbench/doctor.py --live
./start.sh --port 8771
```

The explicit live check reads your account environment and may run a small read-only model probe; it does not create Mosaic templates. Use another port if a different checkout already owns the default port.

Reports separate saved results, structural validation, screenshot capture, Codex observations, and user acceptance. Native sizes, typography, icons, and interactions may differ from the source. Untested behavior is not a pass. Older report text is shown verbatim rather than silently translated.

Update with `git pull` after stopping or completing active runs, then restart the workbench. Personal settings and local run data are not committed. GitHub distributes the tool; its Python service runs on your own machine.
