import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html'
})
export class AppComponent implements OnInit {
  infoServicio: any = null;
  statusRedis: string = 'Cargando...';
  valorContador: number = 0;
  errorMensaje: string = '';

  // Nginx se encargará de redirigir /api al backend en puerto 8080
  private apiUrl = '/api'; 

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.cargarDatosIniciales();
  }

  cargarDatosIniciales() {
    // 1. Obtener estado de la API del endpoint raíz '/'
    this.http.get(`${this.apiUrl}/`).subscribe({
      next: (data: any) => this.infoServicio = data,
      error: () => this.errorMensaje = 'No se pudo conectar con el Backend API.'
    });

    // 2. Obtener el estado de salud/Redis de '/health/ready'
    this.http.get(`${this.apiUrl}/health/ready`).subscribe({
      next: (data: any) => this.statusRedis = data.status,
      error: () => this.statusRedis = 'Desconectado (Redis no disponible)'
    });

    // 3. Obtener el valor actual del contador
    this.http.get(`${this.apiUrl}/counter`).subscribe({
      next: (data: any) => this.valorContador = data.counter,
      error: (err: any) => console.error('Error al traer el contador', err)
    });
  }

  incrementarContador() {
    // Enviar una petición POST a '/counter' para sumar una visita en Redis
    this.http.post(`${this.apiUrl}/counter`, {}).subscribe({
      next: (data: any) => {
        this.valorContador = data.counter;
      },
      error: () => alert('Error al interactuar con Redis a nivel de SO.')
    });
  }
}