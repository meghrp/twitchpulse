<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import ChannelInput from './components/ChannelInput.vue'
import StatsCard from './components/StatsCard.vue'
import SentimentMeter from './components/SentimentMeter.vue'
import TopChatters from './components/TopChatters.vue'
import TopEmotes from './components/TopEmotes.vue'
import MessageFlow from './components/MessageFlow.vue'
import { useWebSocket } from './composables/useWebSocket'

const apiBase = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')
const wsBase = (import.meta.env.VITE_WS_BASE ?? '').replace(/\/$/, '')

const channel = ref('')
const durations = ref([30, 60, 120, 300])
const selectedDuration = ref(60)
const isLoading = ref(false)
const collecting = ref(false)
const errorMessage = ref('')
const infoMessage = ref('')
const sessionId = ref('')
const sessionStatus = ref('Idle')

const stats = reactive({
  messageCount: 0,
  chatterCount: 0,
  topChatters: [],
  topEmotes: [],
  messagesPerMinute: 0,
  sentiment: {
    positivePct: 0,
    negativePct: 0,
    neutralPct: 100,
  },
})

const { status: socketStatus, connect, disconnect } = useWebSocket()

const statusText = computed(() => {
  if (collecting.value) return 'Collecting'
  return sessionStatus.value
})

const isActive = computed(() => collecting.value || ['connecting', 'open'].includes(socketStatus.value))

const apiUrl = (path) => `${apiBase}${path}`
const wsUrl = (id) => {
  if (wsBase) {
    return `${wsBase}/ws/${id}`
  }
  if (apiBase.startsWith('http')) {
    return `${apiBase.replace(/^http/, 'ws')}/ws/${id}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/${id}`
}

const resetStats = () => {
  stats.messageCount = 0
  stats.chatterCount = 0
  stats.topChatters = []
  stats.topEmotes = []
  stats.messagesPerMinute = 0
  stats.sentiment = {
    positivePct: 0,
    negativePct: 0,
    neutralPct: 100,
  }
}

const applyStats = (payload) => {
  stats.messageCount = payload.messageCount ?? stats.messageCount
  stats.chatterCount = payload.chatterCount ?? stats.chatterCount
  stats.topChatters = payload.topChatters ?? stats.topChatters
  stats.topEmotes = payload.topEmotes ?? stats.topEmotes
  stats.messagesPerMinute = payload.messagesPerMinute ?? stats.messagesPerMinute
  stats.sentiment = payload.sentiment ?? stats.sentiment

  if (payload.session?.status && payload.session.status !== 'active') {
    collecting.value = false
    sessionStatus.value = payload.session.status === 'complete' ? 'Complete' : 'Stopped'
    infoMessage.value = payload.session.status === 'complete' ? 'Session finished 🎉' : 'Session stopped'
    disconnect()
    sessionId.value = ''
  }
}

const startAnalysis = async () => {
  if (!channel.value.trim()) {
    errorMessage.value = 'Enter a channel name to begin.'
    return
  }
  infoMessage.value = ''
  errorMessage.value = ''
  isLoading.value = true
  try {
    const response = await fetch(apiUrl('/api/start'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        channel: channel.value.trim(),
        duration_seconds: selectedDuration.value,
      }),
    })
    if (!response.ok) {
      throw new Error('Unable to start session.')
    }
    const data = await response.json()
    sessionId.value = data.session_id
    sessionStatus.value = 'Connecting'
    collecting.value = true
    resetStats()
    connect(wsUrl(sessionId.value), applyStats)
  } catch (error) {
    errorMessage.value = error.message ?? 'Something went wrong.'
    collecting.value = false
  } finally {
    isLoading.value = false
  }
}

const stopAnalysis = async () => {
  if (!sessionId.value) return
  try {
    await fetch(apiUrl('/api/stop'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId.value }),
    })
  } catch (error) {
    console.error(error)
  } finally {
    collecting.value = false
    sessionStatus.value = 'Stopped'
    disconnect()
    sessionId.value = ''
  }
}

const fetchConfig = async () => {
  try {
    const response = await fetch(apiUrl('/api/config'))
    if (!response.ok) return
    const config = await response.json()
    if (config.defaultDuration) {
      selectedDuration.value = config.defaultDuration
    }
    const merged = new Set([...durations.value, config.defaultDuration, config.maxDuration].filter(Boolean))
    durations.value = Array.from(merged).sort((a, b) => a - b)
  } catch (error) {
    console.warn('Config fetch failed', error)
  }
}

onMounted(fetchConfig)
onBeforeUnmount(() => {
  disconnect()
})

watch(
  () => socketStatus.value,
  (value) => {
    if (value === 'open' && collecting.value) {
      sessionStatus.value = 'Live'
    } else if (value === 'connecting') {
      sessionStatus.value = 'Connecting'
    } else if (value === 'error') {
      errorMessage.value = 'Lost connection to the stats feed.'
      collecting.value = false
    }
  },
)
</script>

<template>
  <main>
    <header class="hero">
  <div>
        <p class="eyebrow">TwitchPulse</p>
        <h1>Track the vibe of any Twitch chat in seconds.</h1>
        <p class="tagline">Real-time stats, hype meters, and the hottest emotes — built for viewers.</p>
  </div>
    </header>

    <ChannelInput
      :channel="channel"
      :duration="selectedDuration"
      :durations="durations"
      :is-active="isActive"
      :status-text="statusText"
      :loading="isLoading"
      @update:channel="channel = $event"
      @update:duration="selectedDuration = $event"
      @start="startAnalysis"
      @stop="stopAnalysis"
    />

    <section v-if="errorMessage" class="banner error">
      {{ errorMessage }}
    </section>
    <section v-else-if="infoMessage" class="banner info">
      {{ infoMessage }}
    </section>

    <section class="grid stats">
      <StatsCard label="Messages" icon="💬" glow="#8b5cf6" :value="stats.messageCount" subtext="Total captured" />
      <StatsCard label="Chatters" icon="👥" glow="#f59e0b" :value="stats.chatterCount" subtext="Unique voices" />
      <StatsCard label="Emotes" icon="😀" glow="#ec4899" :value="stats.topEmotes.reduce((sum, e) => sum + e.count, 0)" subtext="Total emotes" />
    </section>

    <section class="grid highlights">
      <MessageFlow :total="stats.messageCount" :per-minute="stats.messagesPerMinute" :socket-status="socketStatus" />
      <SentimentMeter :sentiment="stats.sentiment" />
    </section>

    <section class="grid lists">
      <TopChatters :chatters="stats.topChatters" />
      <TopEmotes :emotes="stats.topEmotes" />
    </section>
  </main>
</template>
