import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface HealthResponse {
  status: string;
}

export interface GeoJsonGeometry {
  type: string;
  coordinates: unknown;
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
}

export interface GewasSummary {
  gewascode: number;
  gewas: string;
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

  getGewassen(): Observable<GewasSummary[]> {
    return this.http.get<GewasSummary[]>('/api/gewassen/');
  }
}
