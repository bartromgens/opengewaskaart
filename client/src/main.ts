import { registerLocaleData } from '@angular/common';
import localeNl from '@angular/common/locales/nl';
import { bootstrapApplication } from '@angular/platform-browser';

import { appConfig } from './app/app.config';
import { App } from './app/app';
import { configureMaplibreWorker } from './maplibre-setup';

// DecimalPipe uses : 'nl-NL' in gewassen.html; bundle locale data for that id.
registerLocaleData(localeNl, 'nl-NL');

configureMaplibreWorker();

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
