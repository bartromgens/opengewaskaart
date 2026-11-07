import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface HealthResponse {
  status: string;
}

export interface GeoJsonGeometry {
  type: string;
  coordinates: unknown;
}

export type GewasGebruikKey = 'veevoer' | 'voedsel' | 'gemengd' | 'niet_voedsel' | 'onbekend';

export interface GewasGebruikMap {
  gewascode: number;
  gebruik: GewasGebruikKey;
}

export interface GebruikSummary {
  gebruik: GewasGebruikKey;
  parcel_count: number;
  area_m2: number | null;
}

export interface Gewasperceel {
  id: number;
  jaar: number;
  gewascode: number;
  gewas: string;
  category: string;
  status: string;
  area_m2: number | null;
  geometry: GeoJsonGeometry;
  gebruik: GewasGebruikKey;
}

export interface GewasSummary {
  gewascode: number;
  gewas: string;
  category: string;
  parcel_count: number;
  area_m2: number | null;
  gebruik: GewasGebruikKey;
  /** True when a GewasGebruik row exists; otherwise `gebruik` defaults to onbekend. */
  gebruik_geclassificeerd: boolean;
}

export interface CategorieSummary {
  category: string;
  parcel_count: number;
  area_m2: number | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('/api/health/');
  }

  getParcel(id: number): Observable<Gewasperceel> {
    return this.http.get<Gewasperceel>(`/api/percelen/${id}/`);
  }

  getGewassen(options?: {
    limit?: number;
    bbox?: string;
    gewasCodes?: readonly number[];
  }): Observable<GewasSummary[]> {
    let params = new HttpParams();
    const limit = options?.limit;
    if (limit !== undefined) {
      params = params.set('limit', String(limit));
    }
    const bbox = options?.bbox;
    if (bbox !== undefined && bbox.length > 0) {
      params = params.set('bbox', bbox);
    }
    const codes = options?.gewasCodes;
    if (codes !== undefined && codes.length > 0) {
      params = params.set('gewas', codes.join(','));
    }
    return this.http.get<GewasSummary[]>('/api/gewassen/', { params });
  }

  getCategorieen(): Observable<CategorieSummary[]> {
    return this.http.get<CategorieSummary[]>('/api/categorieen/');
  }

  getGewasGebruik(): Observable<GewasGebruikMap[]> {
    return this.http.get<GewasGebruikMap[]>('/api/gewasgebruik/');
  }

  getGebruikSummary(): Observable<GebruikSummary[]> {
    return this.http.get<GebruikSummary[]>('/api/gebruik/');
  }
}
