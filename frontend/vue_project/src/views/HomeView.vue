<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api ,{safeRequest} from "@/services/api"
/*
cd vue_project
npm run dev
Localhost:5173
*/



///style= CSS寫法
const router = useRouter()
const total = ref<number | null>(null)

onMounted(async () => {
  const res = await safeRequest(() =>
  api.get("/report/today-total")
    
  )
  if (!res)return
  total.value = res.data.today_total
})

const create_page = () => {
  router.push('create')
}

const all_order = () => {
  router.push('orders')
}

</script>


<template>
  <div style="text-align:center; margin-top:100px;">
    <h1>今日營收</h1>
    <h2 v-if="total !== null">{{ total }}</h2>
    <h2 v-else>載入中...</h2>

    <button 
      style=" font-size:22px;"  
      @click="create_page()">
      創建新訂單
    </button>
        <button 
      style=" font-size:22px;"  
      @click="all_order()">
      全部訂單
    </button>
  </div>
</template>
