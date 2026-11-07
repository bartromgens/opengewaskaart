import { firstValueFrom, type Observable } from 'rxjs';

export async function fetchOr<T>(obs: Observable<T>, fallback: T): Promise<T> {
  try {
    return await firstValueFrom(obs);
  } catch {
    return fallback;
  }
}
