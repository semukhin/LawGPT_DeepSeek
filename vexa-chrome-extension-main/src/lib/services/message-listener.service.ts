import type { StoreKeys } from './storage.service';

export class MessageListenerService {

    private static readonly messages: { 
        [k in MessageType]: { 
            [key: string]: {
                handler: (evtData: any, sender: chrome.runtime.MessageSender, sendResponse: (response?: any) => void) => any,
                sender?: chrome.runtime.MessageSender,
                sendResponse?: (response?: any) => void,
            }
        }
    } = {} as any;
    private static isListenerInitialized = false;

    static initializeListenerService() {
        if (MessageListenerService.isListenerInitialized) {
            console.info('Message listener service has already been initialized');
            return;
        }
        MessageListenerService.registerExtensionMessageEvents();
        console.info('Message listener service initialized successfully');
    }

    static registerMessageListener<T = any, U = any>(messageType: MessageType, handler: (evtData: T, sender: chrome.runtime.MessageSender, sendResponse: any) => U): string {
        const listenerId = MessageListenerService.generateUniqueHandlerID();

        if (!MessageListenerService.messages[messageType]) {
            MessageListenerService.messages[messageType] = {};
        }
        MessageListenerService.messages[messageType][listenerId] = {
            handler
        };
        return listenerId;
    }

    static unRegisterMessageListener(messageType: MessageType, listenerId?: string) {
        if (listenerId) {
            delete MessageListenerService.messages[messageType]?.[listenerId];
        } else {
            delete MessageListenerService.messages?.[messageType];
        }
    }

    private static registerExtensionMessageEvents() {
        chrome.runtime.onMessage.addListener((request: { type: StoreKeys, data: any}, sender, sendResponse) => {
            if(request.type && MessageListenerService.messages[request.type]) {
                const registeredListeners = MessageListenerService.messages[request.type];
                for(const key in registeredListeners) {
                    if(typeof registeredListeners?.[key]?.handler === 'function') {
                        registeredListeners[key].handler(request, sender, sendResponse); // TODO: Add optional sendresponse handling
                    }
                    // return true;
                }
            }
        });
        MessageListenerService.isListenerInitialized = true;
    }

    private static generateUniqueHandlerID() {
        const date = new Date();
        return date.getTime().toString();
    }
}

export enum MessageType {
    INSTALL = 'INSTALL',
    REQUEST_MEDIA_DEVICES = "REQUEST_MEDIA_DEVICES",
    START_RECORDING = "START_RECORDING",
    MEDIA_DEVICES = "MEDIA_DEVICES",
    ON_MICROPHONE_SELECTED = "ON_MICROPHONE_SELECTED",
    MICROPHONE_LEVEL_STATUS = "MICROPHONE_LEVEL_STATUS",
    START_MIC_LEVEL_STREAMING = "START_MIC_LEVEL_STREAMING",
    MIC_LEVEL_STREAM_RESULT = "MIC_LEVEL_STREAM_RESULT",
    OPEN_SETTINGS = "OPEN_SETTINGS",
    REQUEST_START_RECORDING = "REQUEST_START_RECORDING",
    ON_RECORDING_END = "ON_RECORDING_END",
    ON_RECORDING_STARTED = "ON_RECORDING_STARTED",
    STOP_RECORDING = "STOP_RECORDING",
    PAUSE_RECORDING = "PAUSE_RECORDING",
    RESUME_RECORDING = "RESUME_RECORDING",
    TRANSCRIPTION_RESULT = "TRANSCRIPTION_RESULT",
    ASSISTANT_PROMPT_REQUEST = "ASSISTANT_PROMPT_REQUEST",
    ASSISTANT_PROMPT_RESULT = "ASSISTANT_PROMPT_RESULT",
    AUTH_SAVED = "AUTH_SAVED",
    USER_UNAUTHORIZED = "USER_UNAUTHORIZED",
    OFFSCREEN_TRANSCRIPTION_RESULT = "OFFSCREEN_TRANSCRIPTION_RESULT",
    ON_MEDIA_CHUNK_RECEIVED = "ON_MEDIA_CHUNK_RECEIVED",
    DEBUG_MESSAGE = "DEBUG_MESSAGE",
    BACKGROUND_DEBUG_MESSAGE = "BACKGROUND_DEBUG_MESSAGE",
    COPY_TRANSCRIPTION = "COPY_TRANSCRIPTION",
    COPY_TRANSCRIPTION_SUCCESS = "COPY_TRANSCRIPTION_SUCCESS",
    TAB_CHANGED = "TAB_CHANGED",
    ASSISTANT_PROMPT_HISTORY = "ASSISTANT_PROMPT_HISTORY",
    ASSISTANT_HISTORY_REQUEST = "ASSISTANT_HISTORY_REQUEST",
    HAS_RECORDING_HISTORY = "HAS_RECORDING_HISTORY",
    TRANSCRIPTION_HISTORY_REQUEST = "TRANSCRIPTION_HISTORY_REQUEST",
    ON_AUTHENTICATION_SUCCESS = "ON_AUTHENTICATION_SUCCESS",
    LOGIN_SUCCESS = "LOGIN_SUCCESS",
    SPEAKER_EDIT_START = "SPEAKER_EDIT_START",
    UPDATE_SPEAKER_NAME_REQUEST = "UPDATE_SPEAKER_NAME_REQUEST",
    UPDATE_SPEAKER_NAME_RESULT = "UPDATE_SPEAKER_NAME_RESULT",
    SPEAKER_EDIT_COMPLETE = "SPEAKER_EDIT_COMPLETE",
    ASSISTANT_PROMPT_ERROR = "ASSISTANT_PROMPT_ERROR",
    ASSISTANT_ENTRY_EDIT_STARTED = "ASSISTANT_ENTRY_EDIT_STARTED",
    FORK_MESSAGE_CHAIN = "FORK_MESSAGE_CHAIN",

    FETCH_REQUEST = "FETCH_REQUEST",

    THREAD_CREATE = "THREAD_CREATE",
    DELETE_THREAD = "DELETE_THREAD",
    DUPLICATE_THREAD = "DUPLICATE_THREAD",
    THREAD_DELETED = "THREAD_DELETED",
    THREAD_DELETED_ERROR = "THREAD_DELETED_ERROR",
    DELETE_THREAD_START = "DELETE_THREAD_START",
    DELETE_THREAD_COMPLETE = "DELETE_THREAD_COMPLETE",

    OPEN_LOGIN_POPUP = "OPEN_LOGIN_POPUP"
}