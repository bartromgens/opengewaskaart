import { setWorkerUrl } from 'maplibre-gl';

/** Point MapLibre v6 at the worker files copied to the app root via angular.json assets. */
export function configureMaplibreWorker(): void {
  setWorkerUrl(new URL('maplibre-gl-worker.mjs', document.baseURI).href);
}
