/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

export interface Env {
	APP_NAME: string;
	COURSE_NAME: string;
	BUILD_VERSION: string;
	API_TOKEN: string;
	ADMIN_EMAIL: string;
	SETTINGS: KVNamespace;
}

function json(data: unknown, init?: ResponseInit): Response {
	return Response.json(data, init);
}

export default {
	async fetch(request, env): Promise<Response> {
		const url = new URL(request.url);
		const cf = request.cf;
		console.log("request", { path: url.pathname, colo: cf?.colo, country: cf?.country });

		switch (url.pathname) {
			case "/health":
				return json({ status: "ok", version: env.BUILD_VERSION, time: new Date().toISOString() });
			case "/":
				return json({
					app: env.APP_NAME,
					course: env.COURSE_NAME,
					message: "Hello from Cloudflare Workers",
					version: env.BUILD_VERSION,
					time: new Date().toISOString(),
				});
			case "/info":
				return json({
					app: env.APP_NAME,
					course: env.COURSE_NAME,
					version: env.BUILD_VERSION,
				});
			case "/edge":
				return json({
					colo: cf?.colo,
					country: cf?.country,
					city: cf?.city,
					asn: cf?.asn,
					httpProtocol: cf?.httpProtocol,
					tlsVersion: cf?.tlsVersion,
				});
			case "/counter": {
				if (!env.SETTINGS) {
					return json({ error: "KV namespace not bound" }, { status: 500 });
				}
				const raw = await env.SETTINGS.get("visits");
				const visits = Number.parseInt(raw ?? "0", 10) + 1;
				await env.SETTINGS.put("visits", String(visits));
				return json({ visits });
			}
			default:
				return new Response("Not Found", { status: 404 });
		}
	},
} satisfies ExportedHandler<Env>;
