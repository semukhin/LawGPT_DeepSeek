import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent
} from "react"

import "./AssistantList.scss"

import copyIcon from "data-base64:~assets/images/svg/copy-07.svg"
import threadIcon from "data-base64:~assets/images/svg/git-branch-01.svg"
import newMessageIcon from "data-base64:~assets/images/svg/message-plus-square.svg"
import vexaSendIcon from "data-base64:~assets/images/svg/send.svg"
import trashIcon from "data-base64:~assets/images/svg/trash-03.svg"
import {
  ArrowUp,
  Copy,
  GitBranch,
  Loader2,
  MessageCircleWarning,
  Plus,
  PlusCircle,
  Trash
} from "lucide-react"

import { Alert, AlertTitle } from "~components/ui/Alert"
import { Button } from "~components/ui/Button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "~components/ui/Select"
import AsyncMessengerService from "~lib/services/async-messenger.service"
import { MessageType } from "~lib/services/message-listener.service"
import { MessageSenderService } from "~lib/services/message-sender.service"
import { ThreadDeletePromptModal } from "~shared/components/ThreadDeletePromptModal"
import type { ActionButton } from "~shared/components/TranscriptList"
import { sendMessage } from "~shared/helpers/in-content-messaging.helper"
import { getIdFromUrl } from "~shared/helpers/meeting.helper"

import { AssistantEntry } from "../AssistantEntry"
import { BouncingDots } from "../BouncingDots/BouncingDots"

// TODO: place in correct place
const asyncMessengerService = new AsyncMessengerService()

export interface AssistantEntryData {
  current_chain?: number
  user_message?: AssistantMessageUnit
  assistant_message?: AssistantMessageUnit
}

/*
export interface AssistantChains {
  available_chains: (Thread & Option)[];
}

export interface Thread extends Option {
  chain: number;
}
*/

export interface AssistantMessageUnit {
  user_id?: string
  meeting_id: string
  text: string
  role: "user" | "assistant"
  timestamp: string
}

export class ThreadMessage implements AssistantMessageUnit {
  id: string
  user_id?: string
  meeting_id: string | null
  text: string
  meta: object
  role: "user" | "assistant"
  timestamp: string | null

  constructor({
    id = null,
    user_id = null,
    meeting_id = null,
    text = null,
    label = null,
    meta = {},
    role = null,
    timestamp = null
  }) {
    this.id = id
    this.user_id = user_id
    this.meeting_id = meeting_id
    this.text = text
    this.meta = meta || {}
    this.role = role
    this.timestamp = timestamp

    this.label = null !== label ? label : this.meta["label"]
  }

  get label(): string {
    return this.meta["label"] || this.text
  }

  set label(value: string) {
    this.meta["label"] = value
  }

  get isUser() {
    return "user" === this.role
  }

  get isAssistant() {
    return "assistant" === this.role
  }

  cloneWithText(text: string) {
    return new ThreadMessage({ ...this, text: text, label: text })
  }
}

export interface ThreadsResponse {
  total: number
  threads: (Thread & Option)[]
}

class Thread implements Option {
  id: string | null
  title: string | null
  messages?: ThreadMessage[] = []
  created_timestamp?: string

  constructor({
    id = null,
    title = null,
    messages = [],
    created_timestamp = null
  } = {}) {
    this.id = id
    this.title = title
    this.messages = messages.map((m) => new ThreadMessage(m))
    this.created_timestamp = created_timestamp
  }

  get label() {
    return this.title
  }

  set label(value) {
    this.title = value
  }

  get value() {
    return this.id
  }

  set value(value) {
    this.id = value
  }
}

export interface AssistantListProps {
  className?: string
  actionButtonClicked: ActionButton | null
  assistantMessage: string | null
  onActionComplete: () => void
}

export function AssistantList({
  className = "",
  actionButtonClicked,
  assistantMessage,
  onActionComplete
}: AssistantListProps) {
  const MEETING_ID = getIdFromUrl(window.location.href)

  const [userMessage, setUserMessage] = useState<string>("")
  const [userMessagePending, setUserMessagePending] =
    useState<ThreadMessage | null>(null)
  const userMessagePendingRef = useRef(userMessagePending)

  const [threads, setThreads] = useState<Thread[]>(
    AsyncMessengerService.threads
  )
  const [selectedThread, setSelectedThread] = useState<
    (Thread & Option) | undefined
  >(AsyncMessengerService.selectedThread)
  const [threadMessages, setThreadMessages] = useState<ThreadMessage[]>(
    AsyncMessengerService.threadMessages
  )
  const [lastErrorMessage, setLastErrorMessage] = useState<String | null>()

  useEffect(() => {
    AsyncMessengerService.threads = threads
  }, [threads])
  useEffect(() => {
    AsyncMessengerService.threadMessages = threadMessages
  }, [threadMessages])
  useEffect(() => {
    AsyncMessengerService.selectedThread = selectedThread
  }, [selectedThread])

  const [isPrompting, setIsPrompting] = useState(false)
  // const [isThreadsOpen, setIsOpen] = useState(false);

  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isPolling, setIsPolling] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const messagedContainerRef = useRef<HTMLDivElement>(null)
  const bottomDiv = useRef<HTMLDivElement>(null)
  const userMessageInputRef = useRef<HTMLTextAreaElement>(null)

  const isSendingMessageRef = useRef(false)
  const lastErrorMessageTimeoutRef = useRef<number | any>(null)

  const messageSender = new MessageSenderService()
  const [isOpen, setIsOpen] = useState(false)
  const assistantListRef = useRef<HTMLDivElement>(null)

  // TODO: delete?
  const [clearField, setClearField] = useState<boolean>(false)

  const handleThreadChange = (newSelectedThreadId: string) => {
    const newSelectedThread = threads.find((t) => t.id === newSelectedThreadId)
    setSelectedThread(newSelectedThread)
    AsyncMessengerService.selectedThread = newSelectedThread
    setIsOpen(false)
  }

  const onDropdownOpenHandler = () => {
    setIsOpen(true)
  }

  const loadThreadMessages = useCallback(
    (thread: Thread) => {
      asyncMessengerService
        .getRequest(`/api/v1/assistant/messages?thread_id=${thread.id}`)
        .then((messages: ThreadMessage[]) => {
          // Ignore result if the thread changed
          if (selectedThread.id !== thread.id) return

          setThreadMessages(messages.map((m) => new ThreadMessage(m)))
        })
    },
    [selectedThread]
  )

  useEffect(() => {
    setThreadMessages([])
    selectedThread && selectedThread.id && loadThreadMessages(selectedThread)
  }, [loadThreadMessages, selectedThread])

  const onStartNewThread = (
    callback?: (createdThread: Thread & Option) => void
  ) => {
    const emptyThread = threads.find((t) => !t.id)
    if (emptyThread) {
      setSelectedThread(emptyThread)

      return
    }

    const thread = new Thread({
      title: "New thread"
    })
    setThreads((prev) => [...prev, thread])
    setSelectedThread(thread)

    callback && callback(thread)
  }

  const updateThreadFromUserEdit = (message: ThreadMessage) => {
    setUserMessagePending(
      new ThreadMessage({
        text: message.text?.trim() || ""
      })
    )

    setIsPrompting(true)

    setThreadMessages((prev) => {
      const messages = []
      for (let m of prev) {
        if (message.id === m.id) {
          break
        }

        messages.push(m)
      }

      return messages
    })

    asyncMessengerService
      .postRequest(`/api/v1/assistant/messages/edit`, {
        thread_id: selectedThread.id,
        message_id: message.id,
        content: message.text
      })
      .then((response: AssistantEntryData) => {
        if (response.user_message && response.assistant_message) {
          setThreadMessages((prev) => [
            ...prev,
            ...[response.user_message, response.assistant_message].map(
              (m) => new ThreadMessage(m)
            )
          ])
        }
      })
      .catch((err) => {
        setUserMessage(userMessagePendingRef.current.text)
      })
      .finally(() => {
        setUserMessagePending(null)
        userMessagePendingRef.current = null
        setIsPrompting(false)
      })
  }

  const deleteThread = (thread: Thread) => {
    if (!thread.id) {
      onThreadDeleted(thread)
      sendMessage(MessageType.DELETE_THREAD_COMPLETE, {})

      return
    }

    asyncMessengerService
      .deleteRequest(`/api/v1/assistant/threads/delete`, {
        ids: [thread.id]
      })
      .then(
        () => {
          onThreadDeleted(thread)
          sendMessage(MessageType.DELETE_THREAD_COMPLETE, {})
        },
        (error) => {
          alert("Thread delete failed. Try again.")
          // toast('Failed to delete thread. Try again.', { type: 'error' });
        }
      )
  }

  const onThreadDeleted = function (thread: Thread) {
    setThreads((prev) => {
      const threads = prev.filter((t) => t !== thread)
      if (threads.length === 0) {
        onStartNewThread()
      } else {
        setSelectedThread(threads[0])
      }

      return threads
    })
  }

  const [isCreatingNewThread, setIsCreatingNewThread] = useState(false)
  const actionButtonRef = useRef<ActionButton | null>(null)
  const assistantMessageRef = useRef<string | null>(null)

  useEffect(() => {
    if (
      actionButtonClicked &&
      actionButtonClicked !== actionButtonRef.current
    ) {
      actionButtonRef.current = actionButtonClicked
      setIsCreatingNewThread(true)
      createThread(
        actionButtonClicked.prompt,
        actionButtonClicked.name
      ).finally(() => {
        setIsCreatingNewThread(false)
        onActionComplete()
      })
    }
  }, [actionButtonClicked, onActionComplete])

  useEffect(() => {
    if (assistantMessage && assistantMessage !== assistantMessageRef.current) {
      assistantMessageRef.current = assistantMessage
      setIsCreatingNewThread(true)
      createThread(assistantMessage)
        .then(() => {
          setIsCreatingNewThread(false)
          onActionComplete()
        })
        .catch(() => {
          setIsCreatingNewThread(false)
          onActionComplete()
        })
    }
  }, [assistantMessage, onActionComplete])

  const sendUserMessage = useCallback(
    async (event: FormEvent) => {
      event.preventDefault()

      let content = userMessage?.trim()
      if (content?.length === 0) {
        return
      }

      setUserMessage("")

      if (selectedThread?.id) {
        return sendMessageIntoThread(content)
      }

      return createThread(content)
    },
    [userMessagePending, userMessage]
  )

  function sendMessageIntoThread(content: string) {
    content = content.trim()
    userMessagePendingRef.current = new ThreadMessage({
      text: content,
      role: "user"
    })

    setUserMessagePending(userMessagePendingRef.current)

    // post message in thread
    return asyncMessengerService
      .postRequest("/api/v1/assistant/copilot", {
        thread_id: selectedThread.id,
        content
      })
      .then((response: AssistantEntryData) => {
        if (response.user_message && response.assistant_message) {
          setThreadMessages((prev) => [
            ...prev,
            ...[response.user_message, response.assistant_message].map(
              (m) => new ThreadMessage(m)
            )
          ])
        } else {
          setLastErrorMessage(
            "Ooops... can't send message to selected thread. Try again later."
          )
        }
      })
      .catch((err) => {
        setUserMessage(userMessagePendingRef.current.text)
      })
      .finally(() => {
        setUserMessagePending(null)
        userMessagePendingRef.current = null
        setIsPrompting(false)
        isSendingMessageRef.current = false
      })
  }

  const createThread = (prompt: string, label = null) => {
    const newThread = new Thread({
      title: "Starting thread..."
    })

    setThreads((prev) => [...prev, newThread])
    setSelectedThread(newThread)

    userMessagePendingRef.current = new ThreadMessage({
      text: prompt,
      role: "user",
      label
    })

    setUserMessagePending(userMessagePendingRef.current)
    setIsPrompting(true)
    isSendingMessageRef.current = true

    const showErrorMessage = (message: string) => {
      if (lastErrorMessageTimeoutRef.current) {
        clearTimeout(lastErrorMessageTimeoutRef.current)
      }

      setLastErrorMessage(message)

      lastErrorMessageTimeoutRef.current = setTimeout(() => {
        setLastErrorMessage(null)
      }, 4000)
    }

    return asyncMessengerService
      .postRequest("/api/v1/assistant/threads/create", {
        meeting_id: MEETING_ID,
        prompt: prompt,
        meta: { label }
      })
      .then((response: Thread) => {
        if (!response.id || !response.title || !response.messages) {
          showErrorMessage("Ooops... can't create thread. Try again later.")
          return
        }

        newThread.id = response.id
        newThread.title = response.title
        setSelectedThread(newThread)

        setThreadMessages(
          response.messages?.map((m) => new ThreadMessage(m)) || []
        )
      })
      .catch((err) => {
        setUserMessage(userMessagePendingRef.current.text)
      })
      .finally(() => {
        setUserMessagePending(null)
        userMessagePendingRef.current = null
        setIsPrompting(false)
        isSendingMessageRef.current = false
      })
  }

  useEffect(() => {
    const handleClickOutside = (event: Event) => {
      const target = event.target as HTMLElement

      // Ignore clicking special places
      if (
        target.closest("div.ThreadSelected") ||
        target.closest("div.ThreadOption")
      ) {
        return
      }

      setIsOpen(false)
    }
    document.addEventListener("click", handleClickOutside)
    return () => {
      document.removeEventListener("click", handleClickOutside)
    }
  }, [])

  // keep cursor in input fields
  useEffect(() => {
    userMessageInputRef?.current?.focus()
  }, [threadMessages])

  // Auto resize textarea
  useEffect(() => {
    const element = userMessageInputRef?.current

    element.style.height = "5px"
    element.style.height = element.scrollHeight + 5 + "px"
  }, [userMessage])

  useEffect(() => {
    bottomDiv?.current?.scrollIntoView({ behavior: "instant" })
  }, [userMessagePendingRef.current, threadMessages])

  const fetchThreads = function () {
    asyncMessengerService
      .getRequest(`/api/v1/assistant/threads/all?meeting_id=${MEETING_ID}`)
      .then((response: ThreadsResponse) => {
        console.log(response)

        const responseThreads = response.threads
          .map((t) => new Thread(t))
          .sort(
            (a, b) =>
              a.created_timestamp?.localeCompare(b.created_timestamp) || 0
          )

        if (responseThreads?.length) {
          setThreads(responseThreads)

          const thread = responseThreads.find(
            (t) => t.id === AsyncMessengerService.selectedThread?.id
          )
          if (thread) {
            setSelectedThread(thread)
          } else if (!selectedThread) {
            setSelectedThread(responseThreads[0])
            AsyncMessengerService.selectedThread = responseThreads[0]
          }
        }
      })
      .catch((err) => {})
      .finally(() => {})
  }

  // Initial
  let beingCalled = useRef(0)
  useEffect(() => {
    if (beingCalled.current++ !== 0) return

    fetchThreads()
  }, [])

  const [textareaRows, setTextareaRows] = useState(1)

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const content = e.target.value
    setUserMessage(content)

    const lineHeight = 20
    const newRows = Math.min(
      3,
      Math.max(1, Math.floor(e.target.scrollHeight / lineHeight))
    )
    setTextareaRows(newRows)
  }

  return (
    <div
      ref={assistantListRef}
      className={`AssistantList flex flex-col max-h-full w-full h-full overflow-hidden ${className}`}>
      {isCreatingNewThread ? (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <>
          {lastErrorMessage && (
            <div className="px-4">
              <Alert className="relative">
                <MessageCircleWarning className="h-4 w-4" />
                <AlertTitle>{lastErrorMessage}</AlertTitle>
              </Alert>
            </div>
          )}

          <div className="px-2 bg-[#1C1C1C] flex items-center justify-between max-w-full w-full overflow-hidden">
            <div ref={dropdownRef} className="flex-grow flex items-center">
              <Select
                onValueChange={handleThreadChange}
                value={selectedThread?.id}>
                <SelectTrigger className="w-full text-primary bg-[#1C1C1C] border-none">
                  <SelectValue placeholder={<ThreadPlaceholder />}>
                    {selectedThread && (
                      <ThreadSelected
                        value={selectedThread.id}
                        label={selectedThread.label}
                      />
                    )}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent className="dark bg-background border border-border z-[9999999999999]">
                  {threads.length > 0 ? (
                    threads.map((thread) => (
                      <SelectItem key={thread.id} value={thread.id}>
                        {thread.label}
                      </SelectItem>
                    ))
                  ) : (
                    <ThreadNoOption />
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center flex-basis-12">
              {selectedThread && (
                <Button
                  onClick={() =>
                    sendMessage(MessageType.DELETE_THREAD_START, {
                      thread: selectedThread
                    })
                  }
                  variant="ghost"
                  size="icon">
                  <Trash className="size-4 text-muted-foreground" />
                </Button>
              )}
              <Button
                onClick={() => onStartNewThread()}
                variant="ghost"
                size="sm">
                <Plus className="size-4 text-muted-foreground" />
              </Button>
            </div>
          </div>

          {threadMessages?.length || userMessagePending ? (
            <div
              className="flex-1 overflow-y-auto py-4"
              ref={messagedContainerRef}>
              {threadMessages?.map((entry: ThreadMessage, index) => (
                <div key={index}>
                  {entry.isUser && (
                    <AssistantEntry
                      onTextUpdated={updateThreadFromUserEdit}
                      entryData={entry}
                    />
                  )}
                  {entry.isAssistant && <AssistantEntry entryData={entry} />}
                </div>
              ))}

              {userMessagePending && (
                <AssistantEntry
                  key={"pending"}
                  entryData={userMessagePending}
                  pending
                />
              )}

              {isPrompting && (
                <div className="flex flex-grow-0 p-2 w-[fit-content] text-muted-foreground">
                  <BouncingDots />
                </div>
              )}

              <div style={{ height: "10px" }} ref={bottomDiv} />
            </div>
          ) : (
            <div className="flex items-center justify-center flex-grow overflow-hidden">
              <span>
                {isLoadingMessages && !isPolling
                  ? "Loading your chat history..."
                  : 'Type your message. E.g. "What action points were on the call?"'}
              </span>
            </div>
          )}

          <div
            className={`AssistantInput mt-auto pb-2 w-full`}
            style={{ marginTop: "3px" }}>
            <form
              autoComplete="off"
              onSubmit={sendUserMessage}
              className="flex gap-1">
              <div className="relative flex w-full px-4">
                <textarea
                  ref={userMessageInputRef}
                  disabled={isPrompting}
                  value={userMessage}
                  onKeyDown={(e: KeyboardEvent) => {
                    if (e.key === "Enter" && !e.shiftKey) sendUserMessage(e)
                  }}
                  onChange={handleTextareaInput}
                  placeholder="Start typing..."
                  className="flex h-10 pr-5 w-full text-primary rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  style={{
                    resize: "none",
                    maxHeight: "160px",
                    minHeight: "40px",
                    height: `${textareaRows * 20}px`
                  }}
                  name="assistant-input"
                />
                <Button
                  disabled={isPrompting || userMessage?.trim()?.length === 0}
                  type="submit"
                  variant="ghost"
                  className="absolute top-0 right-4"
                  size="icon">
                  <ArrowUp className="size-5 text-primary z-10" />
                </Button>
              </div>
            </form>
          </div>

          <ThreadDeletePromptModal deleteThread={deleteThread} />
        </>
      )}
    </div>
  )
}

const ThreadNoOption: React.FC = () => (
  <p className="whitespace-nowrap text-ellipsis overflow-hidden max-w-full mx-auto text-sm flex items-center">
    No threads
  </p>
)

const ThreadPlaceholder: React.FC = () => (
  <div className="flex gap-2 items-center">
    <GitBranch className="size-4 text-muted-foreground" />
    <p className="flex items-center justify-center min-h-6 text-sm">Threads</p>
  </div>
)

const ThreadSelected: React.FC<{ value: any; label: string }> = (values) => (
  <div className="flex gap-2 items-center w-full">
    <GitBranch className="size-4 text-muted-foreground" />
    <span
      className="text-primary w-auto whitespace-nowrap text-ellipsis flex items-center overflow-hidden text-sm max-w-[214px]"
      title={values.label}>
      {values.label}
    </span>
  </div>
)

const ThreadOption: React.FC<{
  option: Option
  options: Option[]
  selected: boolean
  onClick: () => void
}> = ({ option, options, selected, onClick }) => {
  const newFromThread = () => {
    // sendMessage(MessageType.DELETE_THREAD_START, { thread: option });
  }
  const deleteThread = () => {
    sendMessage(MessageType.DELETE_THREAD_START, { thread: option })
  }

  return (
    <div className="flex w-full justify-between items-center">
      <p
        onClick={onClick}
        className="whitespace-nowrap text-ellipsis overflow-hidden w-full max-w-full text-left text-sm"
        title={option.label}>
        {option.label}
      </p>
      <div className="flex items-center">
        <Button onClick={newFromThread} variant="ghost" size="icon">
          <Copy className="size-4 text-muted-foreground" />
        </Button>

        <Button onClick={deleteThread} variant="ghost" size="icon">
          <Trash className="size-4 text-muted-foreground" />
        </Button>
      </div>
    </div>
  )
}
