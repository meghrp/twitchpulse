<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: {
    type: Number,
    default: 0,
  },
  perMinute: {
    type: Number,
    default: 0,
  },
  socketStatus: {
    type: String,
    default: 'idle',
  },
})

const activityBars = computed(() => {
  const level = Math.min(Math.max(Math.round(props.perMinute / 5), 1), 10)
  return Array.from({ length: 10 }, (_, index) => index < level)
})
</script>

<template>
  <div class="flow">
    <div class="header">
      <p class="eyebrow">Message Flow</p>
      <span class="badge" :class="socketStatus">{{ socketStatus }}</span>
    </div>
    <p class="total">{{ total.toLocaleString() }}</p>
    <p class="subtitle">messages captured</p>
    <div class="frequency">
      <p>{{ perMinute }} / min</p>
      <div class="bars">
        <span
          v-for="(isHot, index) in activityBars"
          :key="index"
          :class="['bar', isHot ? 'hot' : 'cool']"
          :style="{ animationDelay: `${index * 80}ms` }"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.flow {
  border-radius: 22px;
  padding: 1.5rem;
  background: radial-gradient(circle at top, rgba(145, 71, 255, 0.25), rgba(10, 6, 18, 0.95));
  border: 1px solid rgba(255, 255, 255, 0.05);
  text-align: center;
  color: #fff;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: #c8b6ff;
}
.badge {
  font-size: 0.7rem;
  text-transform: uppercase;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  letter-spacing: 0.15em;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.badge.open {
  border-color: rgba(34, 197, 94, 0.5);
  color: #86efac;
}
.badge.connecting {
  color: #fde68a;
  border-color: rgba(253, 230, 138, 0.5);
}
.badge.closed,
.badge.error {
  color: #fca5a5;
  border-color: rgba(248, 113, 113, 0.5);
}
.total {
  margin: 0.4rem 0 0;
  font-size: clamp(2rem, 5vw, 3.4rem);
  font-weight: 800;
}
.subtitle {
  margin: 0;
  color: #c4b8d5;
}
.frequency {
  margin-top: 1.2rem;
}
.frequency p {
  margin: 0;
  font-weight: 600;
  letter-spacing: 0.2em;
  color: #d8cfff;
}
.bars {
  display: flex;
  justify-content: center;
  gap: 0.4rem;
  margin-top: 0.8rem;
}
.bar {
  width: 12px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.12);
  animation: pulse 1.6s ease-in-out infinite;
}
.bar.hot {
  background: linear-gradient(180deg, #f472b6, #c084fc);
  box-shadow: 0 6px 14px rgba(192, 132, 252, 0.45);
}
.bar.cool {
  opacity: 0.3;
}
@keyframes pulse {
  0%,
  100% {
    transform: scaleY(0.6);
  }
  50% {
    transform: scaleY(1);
  }
}
</style>

