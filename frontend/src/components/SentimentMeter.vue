<script setup>
import { computed } from 'vue'

const props = defineProps({
  sentiment: {
    type: Object,
    default: () => ({
      positivePct: 0,
      negativePct: 0,
      neutralPct: 100,
    }),
  },
})

const vibeLabel = computed(() => {
  const positive = props.sentiment.positivePct ?? 0
  if (positive > 70) return { label: 'Hype', emoji: '😄' }
  if (positive > 45) return { label: 'Chill', emoji: '🙂' }
  if (positive > 25) return { label: 'Mixed', emoji: '😐' }
  return { label: 'Salty', emoji: '😠' }
})
</script>

<template>
  <div class="meter">
    <div class="header">
      <h3>🎭 Vibe Check</h3>
      <p>{{ vibeLabel.label }} {{ vibeLabel.emoji }}</p>
    </div>
    <div class="bar">
      <span class="positive" :style="{ width: `${sentiment.positivePct ?? 0}%` }"></span>
      <span class="neutral" :style="{ width: `${sentiment.neutralPct ?? 0}%` }"></span>
      <span class="negative" :style="{ width: `${sentiment.negativePct ?? 0}%` }"></span>
    </div>
    <div class="legend">
      <div>
        <small>Positive</small>
        <strong>{{ (sentiment.positivePct ?? 0).toFixed(0) }}%</strong>
      </div>
      <div>
        <small>Neutral</small>
        <strong>{{ (sentiment.neutralPct ?? 0).toFixed(0) }}%</strong>
      </div>
      <div>
        <small>Negative</small>
        <strong>{{ (sentiment.negativePct ?? 0).toFixed(0) }}%</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.meter {
  padding: 1.3rem;
  border-radius: 24px;
  background: rgba(21, 18, 32, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: #fefcff;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h3 {
  margin: 0;
  font-size: 1.1rem;
}
.bar {
  height: 26px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
  display: flex;
  margin: 0.9rem 0;
}
.positive {
  background: linear-gradient(90deg, #22c55e, #4ade80);
}
.neutral {
  background: linear-gradient(90deg, #a1a1aa, #d4d4d8);
}
.negative {
  background: linear-gradient(90deg, #f87171, #ef4444);
}
.legend {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  color: #b4a1d0;
}
strong {
  display: block;
  margin-top: 0.2rem;
  color: #fff;
  font-size: 0.9rem;
}
</style>

