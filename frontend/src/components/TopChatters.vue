<script setup>
defineProps({
  chatters: {
    type: Array,
    default: () => [],
  },
})
</script>

<template>
  <div class="list">
    <h3>🏆 Top Chatters</h3>
    <ul>
      <li v-if="!chatters.length" class="empty">Waiting for chat to heat up...</li>
      <li v-for="(chatter, index) in chatters" :key="chatter.username" :class="{ leader: index === 0 }">
        <span class="rank">#{{ index + 1 }}</span>
        <div class="info">
          <p class="name">{{ chatter.username }}</p>
          <p class="meta">{{ chatter.count }} messages</p>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.list {
  background: rgba(18, 15, 28, 0.9);
  border-radius: 22px;
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.03);
}
h3 {
  margin: 0 0 0.8rem;
  font-size: 1.1rem;
  color: #f4f1ff;
  font-weight: 600;
}
ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
li {
  display: flex;
  gap: 0.8rem;
  align-items: center;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 16px;
  padding: 0.65rem 0.85rem;
  border: 1px solid transparent;
}
li.leader {
  border-color: rgba(139, 92, 246, 0.4);
  box-shadow: 0 10px 18px rgba(139, 92, 246, 0.15);
}
.rank {
  width: 36px;
  height: 36px;
  border-radius: 14px;
  background: rgba(145, 71, 255, 0.12);
  color: #cdb4ff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}
.info {
  flex: 1;
}
.name {
  margin: 0;
  font-weight: 600;
  color: #f7e7ff;
}
.meta {
  margin: 0.1rem 0 0;
  font-size: 0.85rem;
  color: #9e9ab3;
}
.empty {
  justify-content: center;
  color: #8e86a6;
  border: 1px dashed rgba(255, 255, 255, 0.1);
}
</style>

