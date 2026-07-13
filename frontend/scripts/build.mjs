import { existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

/**
 * fc-app-only ships prebuilt SPA assets under crm/public/frontend/.
 * Frappe Cloud still runs yarn build / yarn production during get-app;
 * this stub verifies those assets exist instead of running Vite.
 */
const appRoot = join(dirname(fileURLToPath(import.meta.url)), "../..");
const indexHtml = join(appRoot, "crm/public/frontend/index.html");

if (!existsSync(indexHtml)) {
	console.error("Prebuilt frontend missing:", indexHtml);
	process.exit(1);
}

console.log("fc-app-only: using prebuilt frontend at", indexHtml);
