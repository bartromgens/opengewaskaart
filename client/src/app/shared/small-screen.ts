import { isPlatformBrowser } from '@angular/common';
import { DestroyRef, PLATFORM_ID, Signal, inject, signal } from '@angular/core';

export const SMALL_SCREEN_MQ = '(max-width: 760px)';

export function injectSmallScreen(): Signal<boolean> {
  const platformId = inject(PLATFORM_ID);
  const destroyRef = inject(DestroyRef);
  const smallScreen = signal(false);

  if (isPlatformBrowser(platformId)) {
    const mq = window.matchMedia(SMALL_SCREEN_MQ);
    const sync = (): void => {
      smallScreen.set(mq.matches);
    };
    sync();
    mq.addEventListener('change', sync);
    destroyRef.onDestroy(() => mq.removeEventListener('change', sync));
  }

  return smallScreen.asReadonly();
}
