import React, { useEffect, useRef, useState } from "react"

import "../global.css"

import vexaBackround from "data-base64:~assets/images/background/vexa-background.png"
import googleMeetLogo from "data-base64:~assets/images/svg/google-meet-logo.svg"
import messageChat from "data-base64:~assets/images/svg/message-chat-circle.svg"
import vexaPermissionsImage from "data-base64:~assets/images/svg/permissions-popup.png"
import searchIcon from "data-base64:~assets/images/svg/search.svg"
import vexaUI from "data-base64:~assets/images/ui/vexa-ui.png"
import { MessageCircle, Search } from "lucide-react"

import {
  StorageService,
  StoreKeys,
  type AuthorizationData
} from "~lib/services/storage.service"
import { BuildInfo, Logo } from "~shared/components"
import { VexaIcon } from "~shared/components/VexaIcon"
import { VexaLogo } from "~shared/components/VexaLogo"

import { Button } from "../components/ui/Button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "../components/ui/Card"
import { Switch } from "../components/ui/Switch"

const OptionsIndex = () => {
  const [hasMediaPermissions, setHasMediaPermissions] = useState(false)
  const [isCheckingToken, setIsCheckingToken] = useState(false)

  const [isLoadingUserSettings, setIsLoadingUserSettings] = useState(false)
  const [doSendInitialChatMessage, setDoSendInitialChatMessage] =
    useState(false)

  const [isClosed, setIsClosed] = useState(false)
  const tokenInputRef = useRef<HTMLInputElement>(null)
  const [_, setVexaToken] = StorageService.useHookStorage<AuthorizationData>(
    StoreKeys.AUTHORIZATION_DATA,
    {
      __vexa_token: "",
      __vexa_main_domain: "",
      __vexa_chrome_domain: ""
    }
  )

  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const getMediaPermissions = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false
      })
      navigator.mediaDevices
        .enumerateDevices()
        .then((devices) => {})
        .catch((error) =>
          console.error("Error getting available microphones:", error)
        )
      setHasMediaPermissions(true)
    } catch (error) {
      console.log("Failed to get media permissions", error)
      setHasMediaPermissions(false)
    }
  }

  const saveToken = (evt) => {
    evt.preventDefault()
    setVexaToken({
      ..._,
      __vexa_token: tokenInputRef.current?.value.trim()
    })
    alert("Token saved!")
    tokenInputRef.current.value = ""
  }

  const checkToken = (evt) => {
    evt.preventDefault()
    setIsCheckingToken(true)
    fetch(
      `${process.env.PLASMO_PUBLIC_CHROME_AWAY_BASE_URL}/api/v1/extension/check-token?token=${tokenInputRef.current?.value.trim()}`
    ).then(
      async (res) => {
        setIsCheckingToken(false)
        if (res.status >= 400) {
          if (res.status == 401) {
            alert("Token IS INCORRECT")
          } else {
            alert("Error occured while checking token")
          }
        } else {
          alert("Token correct")
        }
      },
      (err) => {
        setIsCheckingToken(false)
        alert("Token IS INCORRECT")
      }
    )
  }

  const goToGooleMeet = () => {
    window.open("https://meet.google.com", "__blank")
  }

  const goToVexaDashboard = () => {
    window.open("https://vexa.ai/app", "__blank")
  }

  useEffect(() => {
    getMediaPermissions()
  }, [])

  const onSendInitialChatMessageChanged = (checked: boolean) => {
    setDoSendInitialChatMessage(checked)
    setIsLoadingUserSettings(true)
    setErrorMessage(null)

    StorageService.get<AuthorizationData>(StoreKeys.AUTHORIZATION_DATA, {
      __vexa_token: "",
      __vexa_main_domain: "",
      __vexa_chrome_domain: ""
    }).then((authData) => {
      fetch(
        `${authData["__vexa_main_domain"]}/api/v1/users/update?token=${authData["__vexa_token"]}`,
        {
          method: "PATCH",
          headers: { "Content-type": "application/json" },
          body: JSON.stringify({
            is_allowed_send_init_message: checked
          })
        }
      )
        .then(() => {
          setDoSendInitialChatMessage(checked)
        })
        .catch((error) => {
          console.error("Error updating user settings:", error)
          setTimeout(() => {
            setDoSendInitialChatMessage(false)
            setErrorMessage("Failed to update settings. Please try again.")
          }, 2000)
        })
        .finally(() => {
          setIsLoadingUserSettings(false)
        })
    })
  }

  useEffect(() => {
    setIsLoadingUserSettings(true)

    StorageService.get<AuthorizationData>(StoreKeys.AUTHORIZATION_DATA, {
      __vexa_token: "",
      __vexa_main_domain: "",
      __vexa_chrome_domain: ""
    }).then((authData) => {
      console.log({ authData })

      fetch(
        `${authData["__vexa_main_domain"]}/api/v1/users/me?token=${authData["__vexa_token"]}`
      )
        .then((res) => res.json())
        .then(async (res) => {
          console.log({ res })
          setDoSendInitialChatMessage(res.is_allowed_send_init_message || false)
        })
        .finally(() => {
          setIsLoadingUserSettings(false)
        })
    })
  }, [])

  return (
    <div className="dark w-full h-screen flex bg-background text-foreground overflow-hidden">
      {!hasMediaPermissions || isClosed ? (
        <></>
      ) : (
        <>
          {/* Left side */}
          <div className="w-1/2 p-12 flex flex-col justify-between overflow-y-hidden">
            <VexaLogo className="mb-8" />

            <div className="space-y-8 max-w-md w-full">
              <Card className="bg-card border-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <MessageCircle className="w-6 h-6 text-muted-foreground" />
                    Real-Time Transcription and Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-muted-foreground mb-4">
                    Automatically transcribe meetings and analyze conversations
                    in real-time to capture key points and action items.
                  </CardDescription>
                  <Button
                    onClick={goToGooleMeet}
                    className="w-full flex items-center">
                    <img src={googleMeetLogo} alt="Google Meet" />
                    <span className="text-sm ml-1">Go to Google Meet</span>
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-card border-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Search className="w-6 h-6 text-muted-foreground" />
                    AI-Powered Search & Prompts
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-muted-foreground mb-4">
                    Quickly find relevant information from past meetings and
                    communications using AI-powered search capabilities.
                  </CardDescription>
                  <Button
                    onClick={goToVexaDashboard}
                    className="w-full flex items-center">
                    <VexaIcon fillColor="#000000" size="18" />
                    <span className="text-sm ml-2">Go to Vexa Dashboard</span>
                  </Button>
                </CardContent>
              </Card>

              <div className="flex flex-col space-y-2 px-6">
                <div className="flex items-center space-x-2">
                  <Switch
                    disabled={isLoadingUserSettings}
                    id="send-notification"
                    checked={doSendInitialChatMessage}
                    onCheckedChange={onSendInitialChatMessageChanged}
                  />
                  <label
                    htmlFor="send-notification"
                    className="text-primary text-base">
                    Send notification in the chat about using vexa
                  </label>
                </div>
                {errorMessage && (
                  <p className="pl-[50px] text-xs text-red-500">
                    {errorMessage}
                  </p>
                )}
              </div>
            </div>

            <BuildInfo className="text-muted-foreground mt-8" hideLogo />
          </div>

          {/* Right side */}
          <div className="w-1/2 relative">
            <div className="absolute inset-0 bg-secondary">
              <img
                src={vexaBackround}
                alt="Vexa background"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <img
                src={vexaUI}
                alt="Vexa UI"
                className="max-w-[80%] max-h-[80%] rounded-lg shadow-2xl"
              />
            </div>
          </div>

          {/* Keep the existing modal for permissions */}
          {!hasMediaPermissions && !isClosed && (
            <div className="absolute right-5 top-5 rounded-3xl bg-popover border border-border flex flex-col p-8 w-[360px]">
              <VexaLogo />
              <h2 className="text-base mt-7 font-semibold text-foreground">
                Give Vexa microphone permissions to transcribe your audio
              </h2>
              <p className="text-sm font-normal text-muted-foreground mt-1">
                Don't worry! We never keep your audio stored
              </p>
              <img
                className="my-7"
                src={vexaPermissionsImage}
                alt="Permissions popup"
              />
              <button
                onClick={() => setIsClosed(true)}
                className="text-muted-foreground border border-border rounded-lg p-2 bg-secondary hover:bg-accent">
                Dismiss
              </button>
            </div>
          )}

          {/* Keep the existing hidden form */}
          <form
            action=""
            className="flex-col gap-3 w-96 shadow-md p-4 bg-gray-100 rounded-lg hidden">
            <p className="font-semibold">
              {hasMediaPermissions ? (
                <span className="text-green-500">
                  Microphone permission enabled
                </span>
              ) : (
                <span className="text-red-500">
                  Microphone permission required
                </span>
              )}
            </p>
            <div className="flex flex-col gap-2">
              <label htmlFor="token" className="font-semibold text-gray-600">
                Token
              </label>
              <input
                id="token"
                ref={tokenInputRef}
                type="text"
                name="token"
                className="border rounded-lg w-full p-2 font-semibold text-gray-700"
              />
            </div>
            <div className="flex justify-between w-full">
              <button
                disabled={isCheckingToken}
                onClick={saveToken}
                className="p-3 text-primary font-medium bg-blue-700 rounded-xl">
                Save token
              </button>

              <button
                disabled={isCheckingToken}
                onClick={checkToken}
                className="p-3 text-blue-600 font-bold bg-transparent">
                Check token
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  )
}

export default OptionsIndex
