import { Component, OnInit, AfterViewChecked, ElementRef, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { ScrollPanelModule } from 'primeng/scrollpanel';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageModule } from 'primeng/message';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { AuthService } from '../../../core/services/auth.service';
import { ParentPortalService } from '../parent-portal.service';

@Component({
  selector: 'app-thread-detail',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ButtonModule, InputTextModule, ScrollPanelModule,
    SkeletonModule, MessageModule, ToastModule
  ],
  providers: [MessageService],
  template: `
    <p-toast />

    <div class="flex flex-column" style="height: calc(100vh - 9rem)">
      <!-- Header -->
      <div class="flex align-items-center gap-2 mb-3 flex-shrink-0">
        <i class="pi pi-arrow-left text-primary cursor-pointer" (click)="goBack()"></i>
        <div>
          <div class="font-bold text-900 text-sm">{{ thread?.subject ?? 'Conversation' }}</div>
          @if (thread?.student_name) {
            <div class="text-xs text-500">Re: {{ thread.student_name }}</div>
          }
        </div>
      </div>

      <!-- Loading -->
      @if (loading) {
        <div class="flex flex-column gap-2 flex-1">
          @for (n of [1,2,3]; track n) {
            <p-skeleton height="3rem" borderRadius="12px" />
          }
        </div>
      }

      <!-- Messages scroll area -->
      @if (!loading) {
        <div
          #messagesContainer
          class="flex-1 overflow-y-auto flex flex-column gap-2 pb-2"
          style="overscroll-behavior: contain"
        >
          @if (messages.length === 0) {
            <p-message
              severity="info"
              text="No messages in this conversation yet."
              styleClass="w-full"
            />
          }

          @for (msg of messages; track msg.id) {
            <div
              class="flex"
              [class.justify-content-end]="isOwnMessage(msg)"
              [class.justify-content-start]="!isOwnMessage(msg)"
            >
              <div
                class="px-3 py-2 border-round-xl text-sm"
                style="max-width: 78%; word-break: break-word"
                [style.background]="isOwnMessage(msg) ? '#3b82f6' : '#f1f5f9'"
                [style.color]="isOwnMessage(msg) ? 'white' : '#1e293b'"
              >
                <div>{{ msg.body }}</div>
                <div
                  class="text-xs mt-1"
                  [style.color]="isOwnMessage(msg) ? 'rgba(255,255,255,0.75)' : '#94a3b8'"
                >
                  {{ msg.sender_name }} · {{ msg.created_at | date:'d MMM, h:mm a' }}
                </div>
              </div>
            </div>
          }
        </div>
      }

      <!-- Reply input -->
      @if (!loading) {
        <div class="flex gap-2 pt-2 flex-shrink-0" style="border-top: 1px solid #e2e8f0">
          <input
            pInputText
            [formControl]="replyControl"
            placeholder="Type a message..."
            class="flex-1"
            (keydown.enter)="sendReply()"
          />
          <p-button
            icon="pi pi-send"
            [rounded]="true"
            [loading]="sending"
            [disabled]="replyControl.invalid"
            (onClick)="sendReply()"
          />
        </div>
      }
    </div>

    <style>
      :host ::ng-deep .p-scrollpanel-content { padding: 0 !important; }
    </style>
  `
})
export class ThreadDetailComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;

  private route = inject(ActivatedRoute);
  private portalService = inject(ParentPortalService);
  private auth = inject(AuthService);
  private toast = inject(MessageService);
  private fb = inject(FormBuilder);

  threadId = '';
  thread: any = null;
  messages: any[] = [];
  loading = false;
  sending = false;
  private shouldScrollToBottom = false;

  replyControl = this.fb.control('', Validators.required);

  ngOnInit(): void {
    this.threadId = this.route.snapshot.paramMap.get('threadId') ?? '';
    this.loadThread();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  loadThread(): void {
    this.loading = true;
    this.portalService.getThread(this.threadId).subscribe({
      next: (res) => {
        this.thread = res.data?.thread ?? res.data ?? null;
        this.messages = res.data?.messages ?? res.data?.thread?.messages ?? [];
        this.loading = false;
        this.shouldScrollToBottom = true;
        this.markRead();
      },
      error: () => {
        this.loading = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load conversation.' });
      }
    });
  }

  markRead(): void {
    this.portalService.markThreadRead(this.threadId).subscribe({ error: () => {} });
  }

  sendReply(): void {
    if (this.replyControl.invalid || !this.replyControl.value?.trim()) return;
    this.sending = true;
    const body = this.replyControl.value.trim();

    this.portalService.replyToThread(this.threadId, body).subscribe({
      next: (res) => {
        this.sending = false;
        this.replyControl.reset();
        const newMsg = res.data?.message ?? null;
        if (newMsg) {
          this.messages = [...this.messages, newMsg];
        } else {
          this.loadThread();
        }
        this.shouldScrollToBottom = true;
      },
      error: (err: any) => {
        this.sending = false;
        this.toast.add({ severity: 'error', summary: 'Error', detail: err?.error?.message ?? 'Failed to send.' });
      }
    });
  }

  isOwnMessage(msg: any): boolean {
    const currentUser = this.auth.currentUser();
    return msg.sender_id === currentUser?.id || msg.sender_role === 'parent';
  }

  goBack(): void {
    history.back();
  }

  private scrollToBottom(): void {
    if (this.messagesContainer?.nativeElement) {
      const el = this.messagesContainer.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }
}
