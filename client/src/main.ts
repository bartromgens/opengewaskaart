import { bootstrapApplication } from '@angular/platform-browser';

import { appConfig } from './app/app.config';
import { App } from './app/app';
import { configureMaplibreWorker } from './maplibre-setup';

configureMaplibreWorker();

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));

