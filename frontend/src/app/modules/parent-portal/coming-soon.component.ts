import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-coming-soon',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex align-items-center justify-content-center" style="height: 60vh;">
      <div class="text-center">
        <i class="pi pi-clock text-6xl text-400 mb-4 block"></i>
        <h2 class="text-900 font-medium mb-2">Coming Soon</h2>
        <p class="text-500">This feature is under development.</p>
      </div>
    </div>
  `
})
export class ComingSoonComponent {}
