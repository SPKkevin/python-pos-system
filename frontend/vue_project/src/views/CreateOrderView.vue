<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api ,{safeRequest} from '@/services/api'
type Item = { id: number; name: string; price: number; qty: number }

const router = useRouter()

let nextId = 1
///預設的畫面
const items = ref<Item[]>([
  { id: nextId++, name: '', price: 0, qty: 1 }
])
///新增品項的功能
function addItem() {
  items.value.push({id: nextId++ , name: '', price: 0, qty: 1 })
}

///刪除品項的功能
function deleteItem(index:number) {
  items.value.splice(index, 1)
}

///送出訂單的功能
async function submitOrder() {
  if (!validateItems()) return
  const res = await safeRequest(() =>
  api.post('/orders', {
    items: items.value
    }
    ) 
  )
  if(!res)return
  const order_id = res.data.order_id
  router.push('orders')
  alert(`${order_id}訂單建立成功`)
}


///開單防錯判斷
function validateItems(): boolean {
  for (const [index, it] of items.value.entries()) {
    const nameOk = it.name.trim() !== ''
    const priceOk = it.price > 0
    const qtyOk = it.qty > 0

    if (!nameOk || !priceOk || !qtyOk) {
      alert(`第 ${index + 1} 筆資料不完整`)
      return false
    }
  }
  return true
}


</script>

<template>
  <div style="padding:40px">

    <h1>建立訂單</h1>
    <table>
      <thead>
        <tr>
          <th>品名</th>
          <th>價格(不能是0)</th>
          <th>數量</th>
          <th>操作</th>
        </tr>
      </thead>

      <tbody>
          <tr v-for="(item, index) in items" :key="item.id">
            <td>
              <input v-model="item.name" />
            </td>
            <td>
              <input v-model.number="item.price" type="number" />
            </td>
            <td>
              <input v-model.number="item.qty" type="number" />
            </td>
            <td style="white-space: nowrap;">
              <button @click="deleteItem(index)">刪除品項</button>
            </td>
          </tr>
        </tbody>
    </table>
    <button @click="addItem">新增品項</button>
    <button @click="submitOrder">送出訂單</button>
  </div>
</template>